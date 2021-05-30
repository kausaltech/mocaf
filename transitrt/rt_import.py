import bz2
import time
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict

import pytz
import requests
from psycopg2.extras import execute_values
from django.db import transaction, connection
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.gdal import CoordTransform, SpatialReference

from transitrt.models import VehicleLocation
from gtfs.models import FeedInfo, Route


logger = logging.getLogger(__name__)

MIN_TIME_BETWEEN_LOCATIONS = 2  # in seconds


LOCAL_TZ = pytz.timezone('Europe/Helsinki')

GPS_SRS = SpatialReference('WGS84')
LOCAL_SRS = SpatialReference(settings.LOCAL_SRS)

gps_to_local = CoordTransform(GPS_SRS, LOCAL_SRS)


class TransitRTImporter:
    gtfs_feed: FeedInfo
    routes_by_ref: Dict[str, Route]

    def __init__(self, agency_id: str, url: str = None):
        self.gtfs_feed = FeedInfo.objects.get(agency__id=agency_id)
        self.routes_by_ref = {r.id: r for r in self.gtfs_feed.routes.all()}
        self.cached_journeys = {}
        self.http_url = url
        self.warned_routes = set()
        self._batch = []
        self._batch_jids = set()

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

    def add_vehicle_location(self, act: dict):
        vjid = act['vehicle_journey_ref']
        j = self.cached_journeys.get(vjid)
        if j is not None:
            if act['time'] < j['time'] + timedelta(seconds=MIN_TIME_BETWEEN_LOCATIONS):
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
                if act['time'] < j['time'] + timedelta(seconds=MIN_TIME_BETWEEN_LOCATIONS):
                    continue

            new_objs.append(act)
            self.cached_journeys[vjid] = dict(time=act['time'], vehicle_ref=act['vehicle_ref'])

        self._batch = []
        self._batch_jids = set()

        logger.info('Saving %d observations' % len(new_objs))
        if new_objs:
            self.bulk_insert_locations(new_objs)
        transaction.commit()

    def get_route(self, route_ref: str):
        route = self.routes_by_ref.get(route_ref)
        if route is None:
            if route_ref not in self.warned_routes:
                logger.warn('Route %s not found' % route_ref)
                self.warned_routes.add(route_ref)
        return route

    def bulk_insert_locations(self, objs):
        table_name = VehicleLocation._meta.db_table
        local_srs = settings.LOCAL_SRS

        point = Point(x=0, y=0, srid=4326)

        for obj in objs:
            point.x = obj['loc']['lon']
            point.y = obj['loc']['lat']
            point.transform(gps_to_local)
            obj['x'] = point.x
            obj['y'] = point.y
            obj['gtfs_feed'] = self.gtfs_feed.pk

        query = f"""
            INSERT INTO {table_name}
                (gtfs_route_id, gtfs_feed_id, direction_ref, vehicle_ref, journey_ref, vehicle_journey_ref, time, loc, bearing)
            VALUES %s
        """
        template = "(%(route)s, %(gtfs_feed)s, %(direction_ref)s, %(vehicle_ref)s, "
        template += "%(journey_ref)s, %(vehicle_journey_ref)s, %(time)s, "
        template += f"ST_SetSRID(ST_MakePoint(%(x)s, %(y)s), {local_srs}), %(bearing)s)"

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
            logger.info('Importing from %s' % fn)
            self.update_from_data(f.read())
            file_count += 1
            if file_count == 100:
                self.commit()
                file_count = 0

        self.commit()
        transaction.set_autocommit(True)

    def update_from_url(self, count=1, delay=5000):
        assert count > 0
        transaction.set_autocommit(False)
        while count > 0:
            resp = requests.get(self.http_url, timeout=(10, 30))
            self.update_from_data(resp.content)
            self.commit()
            count -= 1
            if count > 0 and delay:
                time.sleep(delay / 1000)
        transaction.set_autocommit(True)
        # If the route cache becomes too large, just clear it.
        if len(self.routes_by_ref) > 5000:
            self.routes_by_ref = {}
