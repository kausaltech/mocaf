from datetime import datetime, timezone

import orjson
import pytz

from .rt_import import TransitRTImporter


MIN_TIME_BETWEEN_LOCATIONS = 2  # in seconds
FINLAND_BOUNDS = {
    'lat': [59.846373196, 70.1641930203],
    'lon': [20.6455928891, 31.5160921567]
}

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
            self.logger.warn('Route not found: %s' % d['LineRef']['value'])
            route_type = self.ROUTE_TYPE_BUS  # assume bus if no route is found
        else:
            route_type = route.type_id
            route = route.pk
        lon = d['VehicleLocation']['Longitude']
        lat = d['VehicleLocation']['Latitude']
        min_lon, max_lon = FINLAND_BOUNDS['lon']
        min_lat, max_lat = FINLAND_BOUNDS['lat']
        if (lon < min_lon or lon > max_lon or lat < min_lat or lat > max_lat):
            self.logger.info(
                f'Siri import: vehicle coordinates {lat} {lon} outside Finland. Skipping coordinate point.'
            )
            return None

        loc = dict(lon=lon, lat=lat)
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
        original_data = data
        data = orjson.loads(data)

        try:
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
        except AssertionError:
            self.logger.info('Invalid siri data', original_data)
            return

        if 'VehicleActivity' not in data:
            self.logger.info('No vehicle data found')
            return
        data = data['VehicleActivity']

        for act_in in data:
            act = self.import_vehicle_activity(act_in)
            if not act:
                continue
            self.add_vehicle_activity(act, data_ts)
