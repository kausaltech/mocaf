import bz2
import time
import logging
import json
from datetime import datetime, timedelta

import pytz
import requests
from psycopg2.extras import execute_values
from django.db import transaction, connection
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.gdal import CoordTransform, SpatialReference
from multigtfs.models import Route

from transitrt.models import VehicleLocation


logger = logging.getLogger(__name__)


LOCAL_TZ = pytz.timezone('Europe/Helsinki')

coord_transform = ct = CoordTransform(
    SpatialReference('WGS84'), SpatialReference(settings.LOCAL_SRS)
)


def js_to_dt(ts):
    return LOCAL_TZ.localize(datetime.fromtimestamp(ts / 1000))


class SiriImporter:
    def __init__(self):
        self.routes_by_ref = {r.route_id: r for r in Route.objects.all()}
        self.cached_locs = {}
        self._batch = []
        self._batch_vids = set()

    def import_vehicle_activity(self, d):
        time = js_to_dt(d['RecordedAtTime'])
        d = d['MonitoredVehicleJourney']
        loc = Point(d['VehicleLocation']['Longitude'], d['VehicleLocation']['Latitude'], srid=4326)
        loc.transform(coord_transform)
        route = self.routes_by_ref[d['LineRef']['value']].id
        jr = d['FramedVehicleJourneyRef']
        journey_ref = '%s:%s' % (jr['DataFrameRef']['value'], jr['DatedVehicleJourneyRef'])

        return dict(
            time=time,
            vehicle_ref=d['VehicleRef']['value'],
            route=route,
            direction_ref=d['DirectionRef']['value'],
            loc=loc,
            journey_ref=journey_ref,
            bearing=d['Bearing'],
        )

    def update_cached_locs(self, vehicle_ids):
        to_fetch = set()
        for vid in vehicle_ids:
            if vid not in self.cached_locs:
                to_fetch.add(vid)
        if not to_fetch:
            return

        locs = VehicleLocation.objects.filter(vehicle_ref__in=vehicle_ids)\
            .values('vehicle_ref', 'time').distinct('vehicle_ref')\
            .order_by('vehicle_ref', '-time')
        for x in locs:
            self.cached_locs[x['vehicle_ref']] = x['time']

    def update_from_siri(self, data):
        assert len(data) == 1
        data = data['Siri']
        assert len(data) == 1
        data = data['ServiceDelivery']

        data_ts = js_to_dt(data['ResponseTimestamp'])
        data = data['VehicleMonitoringDelivery']
        assert len(data) == 1
        data = data[0]
        resp_ts = js_to_dt(data['ResponseTimestamp'])
        assert data_ts == resp_ts
        if 'VehicleActivity' not in data:
            logger.info('No vehicle data found')
            return
        data = data['VehicleActivity']

        for act_in in data:
            act = self.import_vehicle_activity(act_in)
            if abs((data_ts - act['time']).total_seconds()) > 60:
                logger.warn('Refusing too long time difference for %s (%s)' % (act['vehicle_ref'], act['time']))
                continue

            vid = act['vehicle_ref']
            last_time = self.cached_locs.get(vid)
            if last_time and last_time + timedelta(seconds=1) >= act['time']:
                continue
            self._batch_vids.add(act['vehicle_ref'])
            self._batch.append(act)

    def bulk_insert_locations(self, objs):
        table_name = VehicleLocation._meta.db_table
        local_srs = settings.LOCAL_SRS
        for obj in objs:
            obj['x'] = obj['loc'].x
            obj['y'] = obj['loc'].y

        query = f"""
            INSERT INTO {table_name}
                (route_id, direction_ref, vehicle_ref, journey_ref, time, loc, bearing)
            VALUES %s
        """
        template = "(%(route)s, %(direction_ref)s, %(vehicle_ref)s, "
        template += "%(journey_ref)s, %(time)s, "
        template += f"ST_SetSRID(ST_MakePoint(%(x)s, %(y)s), {local_srs}), %(bearing)s)"

        with connection.cursor() as cursor:
            execute_values(cursor, query, objs, template=template, page_size=2048)

    def commit(self):
        self.update_cached_locs(self._batch_vids)
        new_objs = []
        for act in self._batch:
            vid = act['vehicle_ref']
            last_time = self.cached_locs.get(vid)
            # Ensure the new sample is fresh enough
            if last_time and last_time + timedelta(seconds=1) >= act['time']:
                continue

            new_objs.append(act)
            self.cached_locs[vid] = act['time']

        self._batch = []
        self._batch_vids = set()

        logger.info('Saving %d observations' % len(new_objs))
        if not new_objs:
            return

        self.bulk_insert_locations(new_objs)
        transaction.commit()

    def update_from_files(self, fns):
        transaction.set_autocommit(False)
        file_count = 0

        for fn in fns:
            if fn.endswith('.bz2'):
                f = bz2.open(fn, 'r')
            else:
                f = open(fn, 'r')
            data = json.load(f)
            logger.info('Importing from %s' % fn)
            self.update_from_siri(data)
            file_count += 1
            if file_count == 100:
                self.commit()
                file_count = 0
        if file_count:
            self.commit()
        transaction.set_autocommit(True)

    def update_from_url(self, url, count=1, delay=5000):
        transaction.set_autocommit(False)
        while count > 0:
            resp = requests.get(url, timeout=(10, 30))
            data = resp.json()
            self.update_from_siri(data)
            self.commit()
            count -= 1
            if count > 0 and delay:
                time.sleep(delay / 1000)
        transaction.set_autocommit(True)
