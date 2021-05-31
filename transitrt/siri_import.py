import logging
from datetime import datetime, timedelta, timezone

import orjson
import pytz

from .rt_import import TransitRTImporter


MIN_TIME_BETWEEN_LOCATIONS = 2  # in seconds


LOCAL_TZ = pytz.timezone('Europe/Helsinki')


def js_to_dt(ts):
    return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


def make_vehicle_journey_id(act):
    return '%s:%s' % (act['journey_ref'], act['vehicle_ref'])


class SiriImporter(TransitRTImporter):
    def import_vehicle_activity(self, d):
        dt = js_to_dt(d['RecordedAtTime'])
        d = d['MonitoredVehicleJourney']

        route = self.get_route(d['LineRef']['value'])
        if route is None:
            self.logger.warn('Route not found')
            route_type = self.ROUTE_TYPE_BUS  # assume bus if no route is found
        else:
            route_type = route.type_id
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
            route_type=route_type,
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
            self.logger.info('No vehicle data found')
            return
        data = data['VehicleActivity']

        for act_in in data:
            act = self.import_vehicle_activity(act_in)
            if not act:
                continue
            self.add_vehicle_activity(act, data_ts)
