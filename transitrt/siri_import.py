import bz2
import time
import logging
import orjson
from datetime import datetime, timedelta, timezone

import pytz
import requests
from django.db import transaction
from django.conf import settings
from django.contrib.gis.gdal import CoordTransform, SpatialReference

from .rt_import import TransitRTImporter

logger = logging.getLogger(__name__)

MIN_TIME_BETWEEN_LOCATIONS = 2  # in seconds


LOCAL_TZ = pytz.timezone('Europe/Helsinki')

GPS_SRS = SpatialReference('WGS84')
LOCAL_SRS = SpatialReference(settings.LOCAL_SRS)

coord_transform = CoordTransform(GPS_SRS, LOCAL_SRS)


def js_to_dt(ts):
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


def dt_to_str(dt):
    return dt.astimezone(LOCAL_TZ).replace(microsecond=0).isoformat()


def make_vehicle_journey_id(act):
    return '%s:%s' % (act['journey_ref'], act['vehicle_ref'])


class SiriImporter(TransitRTImporter):
    def import_vehicle_activity(self, d):
        dt = js_to_dt(d['RecordedAtTime'])
        d = d['MonitoredVehicleJourney']

        route = self.get_route(d['LineRef']['value'])
        if route is None:
            logger.warn('Route not found')
        else:
            route = route.pk

        loc = dict(lon=d['VehicleLocation']['Longitude'], lat=d['VehicleLocation']['Latitude'])
        jr = d['FramedVehicleJourneyRef']
        journey_ref = '%s:%s' % (jr['DataFrameRef']['value'], jr['DatedVehicleJourneyRef'])

        act = dict(
            time=dt,
            vehicle_ref=d['VehicleRef']['value'],
            gtfs_route=route,
            direction_ref=d['DirectionRef']['value'],
            loc=loc,
            journey_ref=journey_ref,
            bearing=d['Bearing'],
            route=route,
        )
        act['vehicle_journey_ref'] = make_vehicle_journey_id(act)
        return act

    def update_from_data(self, data: bytes):
        data = orjson.loads(data)

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

        if not hasattr(self, 'latest_data_time'):
            self.latest_data_time = data_ts
        elif data_ts > self.latest_data_time:
            self.latest_data_time = data_ts

        for act_in in data:
            act = self.import_vehicle_activity(act_in)
            if not act:
                continue
            vjid = act['vehicle_journey_ref']
            if act['time'] > data_ts + timedelta(seconds=5):
                logger.warn('Vehicle time for %s is too much in the future (%s)' % (vjid, dt_to_str(act['time'])))
                continue
            if act['time'] < data_ts - timedelta(seconds=120):
                logger.warn('Vehicle time for %s is too much in the past (%s)' % (vjid, dt_to_str(act['time'])))
                continue
            j = self.cached_journeys.get(vjid)
            if j is not None:
                if act['time'] < j['time'] + timedelta(seconds=MIN_TIME_BETWEEN_LOCATIONS):
                    continue
            self._batch_jids.add(vjid)
            self._batch.append(act)
