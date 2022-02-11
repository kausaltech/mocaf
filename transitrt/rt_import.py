import bz2
import time
import logging
from datetime import datetime, timedelta
from typing import Dict

import pytz
import requests
from psycopg2.extras import execute_values
from django.db import transaction, connection
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.gdal import CoordTransform, SpatialReference

from transitrt.models import VehicleLocation
from trips.models import TransportMode
from gtfs.models import FeedInfo, Route
from .exceptions import CommonTaskFailure


MIN_TIME_BETWEEN_SAMPLES = 2  # in seconds
MAX_TIME_IN_FUTURE = 5  # s
MAX_TIME_IN_PAST = 120  # s

LOCAL_TZ = pytz.timezone('Europe/Helsinki')

GPS_SRS = SpatialReference('WGS84')
LOCAL_SRS = SpatialReference(settings.LOCAL_SRS)

gps_to_local = CoordTransform(GPS_SRS, LOCAL_SRS)


class TransitRTImporter:
    ROUTE_TYPE_TRAM = 0
    ROUTE_TYPE_SUBWAY = 1
    ROUTE_TYPE_TRAIN = 2
    ROUTE_TYPE_BUS = 3

    id: str
    logger: logging.Logger
    gtfs_feed: FeedInfo
    routes_by_ref: Dict[str, Route]
    modes_by_id: Dict[str, TransportMode]
    min_time_between_samples: int = MIN_TIME_BETWEEN_SAMPLES
    max_time_in_future: int = MAX_TIME_IN_FUTURE
    max_time_in_past: int = MAX_TIME_IN_PAST

    def __init__(self, id: str, feed_publisher_name: str = None, agency_id: str = None, agency_name: str = None, url: str = None):
        self.id = id

        self.logger = logging.getLogger('transitrt.%s' % id)

        qs = FeedInfo.objects
        if feed_publisher_name:
            qs = qs.filter(feed_publisher_name=feed_publisher_name)
        if agency_id:
            qs = qs.filter(agencies__id=agency_id)
        if agency_name:
            qs = qs.filter(agencies__name=agency_name)
        qs = qs.order_by('-feed_start_date')

        self.gtfs_feed = qs.first()
        self.routes_by_ref = {r.short_name: r for r in self.gtfs_feed.routes.all()}
        self.modes_by_id = {m.identifier: m for m in TransportMode.objects.all()}
        self.cached_journeys = {}
        if url is not None:
            self.http_url = url
        self.warned_routes = set()
        self._batch = []
        self._batch_jids = set()

    def dt_to_str(self, dt):
        return dt.astimezone(LOCAL_TZ).replace(microsecond=0).isoformat()

    def update_cached_locs(self, journey_ids):
        journey_refs_to_fetch = set()
        for jid in journey_ids:
            if jid not in self.cached_journeys:
                journey_refs_to_fetch.add(jid)

        if not journey_refs_to_fetch:
            return

        # Find the latest data points we already have for these journeys
        locs = (
            VehicleLocation.objects.filter(vehicle_journey_ref__in=journey_refs_to_fetch)
            .filter(time__lte=self.latest_data_time + timedelta(hours=24))
            .filter(time__gte=self.latest_data_time - timedelta(hours=24))
            .values('vehicle_journey_ref', 'time').distinct('vehicle_journey_ref')
            .order_by('vehicle_journey_ref', '-time')
        )
        for x in locs:
            self.cached_journeys[x['vehicle_journey_ref']] = dict(
                time=x['time'],
            )

    def add_vehicle_activity(self, act: dict, data_ts: datetime):
        if not hasattr(self, 'latest_data_time'):
            self.latest_data_time = data_ts
        elif data_ts > self.latest_data_time:
            self.latest_data_time = data_ts

        vjid = act['vehicle_journey_ref']
        if act['time'] > data_ts + timedelta(seconds=self.max_time_in_future):
            self.logger.warn('Vehicle time for %s is too much in the future (%s)' % (vjid, self.dt_to_str(act['time'])))
            return
        if act['time'] < data_ts - timedelta(seconds=self.max_time_in_past):
            self.logger.warn('Vehicle time for %s is too much in the past (%s)' % (vjid, self.dt_to_str(act['time'])))
            return

        j = self.cached_journeys.get(vjid)
        if j is not None:
            if act['time'] < j['time'] + timedelta(seconds=self.min_time_between_samples):
                return
        self._batch_jids.add(vjid)
        self._batch.append(act)

    def commit(self):
        self.update_cached_locs(self._batch_jids)
        new_objs = []
        for act in self._batch:
            vjid = act['vehicle_journey_ref']
            j = self.cached_journeys.get(vjid)
            # Ensure the new sample is fresh enough
            if j is not None:
                if act['time'] < j['time'] + timedelta(seconds=self.min_time_between_samples):
                    continue

            new_objs.append(act)
            self.cached_journeys[vjid] = dict(time=act['time'], vehicle_ref=act['vehicle_ref'])

        self._batch = []
        self._batch_jids = set()

        self.logger.info('Saving %d observations' % len(new_objs))
        if new_objs:
            self.bulk_insert_locations(new_objs)
        transaction.commit()

    def get_route(self, route_ref: str):
        route = self.routes_by_ref.get(route_ref)
        if route is None:
            if route_ref not in self.warned_routes:
                self.logger.warn('Route %s not found' % route_ref)
                self.warned_routes.add(route_ref)
        return route

    def bulk_insert_locations(self, objs):
        table_name = VehicleLocation._meta.db_table
        local_srs = settings.LOCAL_SRS

        # Reuse the same point object for better performance
        point = Point(x=0, y=0, srid=4326)

        for obj in objs:
            point.x = obj['loc']['lon']
            point.y = obj['loc']['lat']
            point.transform(gps_to_local)
            obj['x'] = point.x
            obj['y'] = point.y
            obj['gtfs_feed'] = self.gtfs_feed.pk
            if 'bearing' not in obj:
                obj['bearing'] = None
            if 'speed' not in obj:
                obj['speed'] = None

        query = f"""
            INSERT INTO {table_name}
                (gtfs_route_id, gtfs_feed_id, direction_ref, vehicle_ref,
                journey_ref, vehicle_journey_ref, time, loc, bearing,
                speed, route_type)
            VALUES %s
            ON CONFLICT (time, vehicle_journey_ref) DO NOTHING
        """
        template = "(%(route)s, %(gtfs_feed)s, %(direction_ref)s, %(vehicle_ref)s, "
        template += "%(journey_ref)s, %(vehicle_journey_ref)s, %(time)s, "
        template += f"ST_SetSRID(ST_MakePoint(%(x)s, %(y)s), {local_srs}), "
        template += "%(bearing)s, %(speed)s, %(route_type)s)"

        with connection.cursor() as cursor:
            execute_values(cursor, query, objs, template=template, page_size=2048)

    def update_from_files(self, fns):
        transaction.set_autocommit(False)
        file_count = 0

        for fn in fns:
            if fn.endswith('.bz2'):
                f = bz2.open(fn, 'rb')
            else:
                f = open(fn, 'rb')
            self.logger.info('Importing from %s' % fn)
            self.update_from_data(f.read())
            file_count += 1
            if file_count == 100:
                self.commit()
                file_count = 0

        self.commit()
        transaction.set_autocommit(True)

    def perform_http_query(self):
        resp = requests.get(self.http_url, timeout=(10, 10))
        resp.raise_for_status()
        return resp.content

    def update_from_url(self, count=1, delay=5000):
        assert count > 0
        transaction.set_autocommit(False)
        while count > 0:
            try:
                resp = self.perform_http_query()
            except (requests.ReadTimeout, requests.ConnectTimeout, requests.ConnectionError):
                raise CommonTaskFailure('There was a network error when retrieving siri live data.')
            self.update_from_data(resp)
            self.commit()
            count -= 1
            if count > 0 and delay:
                time.sleep(delay / 1000)
        transaction.set_autocommit(True)
        # If the route cache becomes too large, just clear it.
        if len(self.cached_journeys) > 2000:
            self.cached_journeys = {}


def make_importer(importer_id):
    conf = settings.TRANSITRT_IMPORTERS[importer_id].copy()
    conf.pop('frequency', None)
    importer_type = conf.pop('type')
    if importer_type == 'siri-rt':
        from .siri_import import SiriImporter
        importer_class = SiriImporter
    elif importer_type == 'rata':
        from .rata_import import RataImporter
        importer_class = RataImporter

    rt_importer = importer_class(id=importer_id, **conf)
    return rt_importer
