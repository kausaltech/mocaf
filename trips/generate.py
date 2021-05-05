import logging
import geopandas as gpd

from calc.trips import (
    LOCAL_2D_CRS, LOCAL_TZ, read_trips, read_uuids, split_trip_legs, filter_trips
)

from utils.perf import PerfCounter
from django.db import transaction, connection
from django.db.models import Q, Max
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import Point
from django.utils import timezone
from psycopg2.extras import execute_values
from trips.models import Device, TransportMode, Trip, Leg, LegLocation
from trips_ingest.models import Location


logger = logging.getLogger(__name__)

LEG_LOCATION_TABLE = LegLocation._meta.db_table

local_crs = SpatialReference(LOCAL_2D_CRS)
gps_crs = SpatialReference(4326)
coord_transform = CoordTransform(local_crs, gps_crs)


# Transform to GPS coordinates
def make_point(x, y):
    pnt = Point(x, y, srid=LOCAL_2D_CRS)
    pnt.transform(coord_transform)
    return pnt


def generate_leg_location_rows(leg, df):
    rows = df.apply(lambda row: (
        leg.id,
        row.lon, row.lat,
        '%s' % str(row.time),
        row.speed,
    ), axis=1)
    return list(rows.values)


class TripGenerator:
    def __init__(self):
        transport_modes = {x.identifier: x for x in TransportMode.objects.all()}
        self.atype_to_mode = {
            'walking': transport_modes['walk'],
            'on_foot': transport_modes['walk'],
            'in_vehicle': transport_modes['car'],
            'running': transport_modes['walk'],
            'on_bicycle': transport_modes['bicycle'],
        }

    def insert_leg_locations(self, rows):
        pc = PerfCounter('save_locations', show_time_to_last=True)
        query = f'''INSERT INTO {LEG_LOCATION_TABLE} (
            leg_id, loc, time, speed
        ) VALUES %s'''

        with connection.cursor() as cursor:
            pc.display('after cursor')
            value_template = """(
                    %s,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                    %s :: timestamptz,
                    %s
            )"""
            execute_values(
                cursor, query, rows, template=value_template, page_size=10000
            )

        pc.display('after insert')

    def save_leg(self, trip, df, last_ts):
        start = df.iloc[0][['time', 'x', 'y']]
        end = df.iloc[-1][['time', 'x', 'y']]

        leg_length = df['distance'].sum()

        # Ensure trips are ordered properly
        assert start.time >= last_ts and end.time >= last_ts

        mode = self.atype_to_mode[df.iloc[0].atype]

        leg = Leg(
            trip=trip,
            mode=mode,
            length=leg_length,
            start_time=start.time,
            end_time=end.time,
            start_loc=make_point(start.x, start.y),
            end_loc=make_point(end.x, end.y),
        )
        leg.update_carbon_footprint()
        leg.save()

        rows = generate_leg_location_rows(leg, df)

        return rows, end.time

    def save_trip(self, uid, df):
        pc = PerfCounter('generate_trips', show_time_to_last=True)
        if not len(df):
            print('No samples, returning')
            return

        device = Device.objects.filter(uuid=uid).first()

        pc.display('start')

        min_time = df.time.min()
        max_time = df.time.max()

        df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y, crs=LOCAL_2D_CRS))
        pc.display('after create gdf for %d points' % len(df))
        df['geometry'] = df['geometry'].to_crs(4326)
        df['lon'] = df.geometry.x
        df['lat'] = df.geometry.y
        pc.display('after crs for %d points' % len(df))

        # Delete trips that overlap with our data
        overlap = Q(end_time__gte=min_time) & Q(end_time__lte=max_time)
        overlap |= Q(start_time__gte=min_time) & Q(start_time__lte=max_time)
        legs = Leg.objects.filter(trip__device=device).filter(overlap)
        count = device.trips.filter(legs__in=legs).delete()
        print(count)
        pc.display('deleted')

        last_ts = df.time.min()

        # Create trips
        all_rows = []

        trip = Trip(device=device)
        trip.save()
        pc.display('trip save')

        leg_ids = df.leg_id.unique()
        for leg_id in leg_ids:
            leg_df = df[df.leg_id == leg_id]
            leg_rows, last_ts = self.save_leg(trip, leg_df, last_ts)
            all_rows += leg_rows

        pc.display('after leg location generation')
        self.insert_leg_locations(all_rows)
        pc.display('after leg location insert')

    def begin(self):
        transaction.set_autocommit(False)

    def generate_trips(self, uuid, start_time, end_time):
        device = Device.objects.filter(uuid=uuid).first()
        if device is None:
            raise Exception('Device %s not found' % uuid)

        pc = PerfCounter('update trips for %s' % uuid, show_time_to_last=True)
        df = read_trips(connection, uuid, start_time=start_time, end_time=end_time)
        if df is None or not len(df):
            return
        pc.display('read done, got %d rows' % len(df))

        for trip_id in df.trip_id.unique():
            trip_df = df[df.trip_id == trip_id].copy()
            print('trip with %d samples' % len(trip_df))
            try:
                trip_df = filter_trips(trip_df)
            except Exception as e:
                logger.error(e)
                continue
            pc.display('filter done')
            trip_df['atype'] = trip_df['atypef']
            trip_df['x'] = trip_df['xf']
            trip_df['y'] = trip_df['yf']
            # Use the fixed versions of columns
            trip_df = split_trip_legs(connection, trip_df)
            pc.display('legs split')
            with transaction.atomic():
                self.save_trip(uuid, trip_df)
            pc.display('trip saved')
        transaction.commit()

    def find_uuids_with_new_samples(self):
        devices = (
            Device.objects.annotate(
                last_leg_received_at=Max('trips__legs__received_at'),
                last_leg_end_time=Max('trips__legs__end_time')
            ).values('uuid', 'last_leg_received_at', 'last_leg_end_time').exclude(last_leg_received_at=None)
        )
        last_leg_by_uuid = {
            x['uuid']: dict(received_at=x['last_leg_received_at'], end_time=x['last_leg_end_time'])
            for x in devices
        }
        uuids = (
            Location.objects.values('uuid').annotate(newest_created_at=Max('created_at')).order_by()
                .values('uuid', 'newest_created_at')
        )
        uuids_to_process = []
        for row in uuids:
            uuid = row['uuid']
            newest_created_at = row['newest_created_at']

            last_leg = last_leg_by_uuid.get(uuid)
            if not last_leg or newest_created_at > last_leg['received_at']:
                uuids_to_process.append([
                    uuid,
                    last_leg['end_time'] if last_leg else None
                ])

        return uuids_to_process

    def generate_new_trips(self):
        uuids = self.find_uuids_with_new_samples()
        now = timezone.now()
        for uuid, last_leg_end in uuids:
            if last_leg_end:
                start_time = last_leg_end
                end_time = now
            else:
                start_time = None
                end_time = None
            self.generate_trips(uuid, start_time=start_time, end_time=end_time)

    def end(self):
        transaction.commit()
        transaction.set_autocommit(True)


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv()
    eng = create_engine(os.getenv('DATABASE_URL'))
    conn = eng.connect()

    all_uids = read_uuids(eng)
