from datetime import datetime, timedelta
import logging
from typing import Optional
import sentry_sdk
import geopandas as gpd

from calc.trips import (
    LOCAL_2D_CRS, read_locations, read_uuids, split_trip_legs, filter_trips
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


class GeneratorError(Exception):
    pass


class TripGenerator:
    def __init__(self, force=False):
        self.force = force
        transport_modes = {x.identifier: x for x in TransportMode.objects.all()}
        self.atype_to_mode = {
            'walking': transport_modes['walk'],
            'on_foot': transport_modes['walk'],
            'in_vehicle': transport_modes['car'],
            'running': transport_modes['walk'],
            'on_bicycle': transport_modes['bicycle'],
            'bus': transport_modes['bus'],
            'tram': transport_modes['tram'],
            'train': transport_modes['train'],
        }

    def insert_leg_locations(self, rows):
        # Having "None" as the speed column is a periodically recurring
        # issue. Raise error to continue with other uuids if None found
        # in speed column
        try:
            next(x for x in rows if x[4] is None)
            raise GeneratorError('Encountered invalid value None as speed for leg')
        except StopIteration:
            pass
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

    def save_leg(self, trip, df, last_ts, default_variants, pc):
        start = df.iloc[0][['time', 'x', 'y']]
        end = df.iloc[-1][['time', 'x', 'y']]
        received_at = df.iloc[-1].created_at

        leg_length = df['distance'].sum()

        # Ensure trips are ordered properly
        assert start.time >= last_ts and end.time >= last_ts

        mode = self.atype_to_mode[df.iloc[0].atype]
        variant = default_variants.get(mode)

        leg = Leg(
            trip=trip,
            mode=mode,
            mode_variant=variant,
            estimated_mode=mode,
            length=leg_length,
            start_time=start.time,
            end_time=end.time,
            start_loc=make_point(start.x, start.y),
            end_loc=make_point(end.x, end.y),
            received_at=received_at,
        )
        leg.update_carbon_footprint()
        leg.save()
        rows = generate_leg_location_rows(leg, df)
        pc.display(str(leg))

        return rows, end.time

    def save_trip(self, device, df, default_variants):
        pc = PerfCounter('generate_trips', show_time_to_last=True)
        if not len(df):
            print('No samples, returning')
            return

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

        if not self.force:
            if legs.filter(
                Q(feedbacks__isnull=False) | Q(user_corrected_mode__isnull=False) | Q(user_corrected_mode_variant__isnull=False)
            ).exists():
                logger.info('Legs have user corrected elements, not deleting')
                return

        if not self.force:
            if device.trips.filter(legs__in=legs).filter(feedbacks__isnull=False):
                logger.info('Trips have user corrected elements, not deleting')
                return

        count = device.trips.filter(legs__in=legs).delete()
        pc.display('deleted')

        last_ts = df.time.min()

        # Create trips
        all_rows = []

        trip = Trip(device=device)
        trip.save()
        pc.display('trip %d saved' % trip.id)

        leg_ids = df.leg_id.unique()
        for leg_id in leg_ids:
            leg_df = df[df.leg_id == leg_id]
            leg_rows, last_ts = self.save_leg(trip, leg_df, last_ts, default_variants, pc)
            all_rows += leg_rows

        pc.display('generated %d legs' % len(leg_ids))
        self.insert_leg_locations(all_rows)
        pc.display('updating carbon footprint')
        trip.update_device_carbon_footprint()
        pc.display('trip %d save done' % trip.id)

    def begin(self):
        transaction.set_autocommit(False)

    def process_trip(self, device, df):
        pc = PerfCounter('process_trip')
        logger.info('%s: %s: trip with %d samples' % (str(device), df.time.min(), len(df)))
        df = filter_trips(df)
        pc.display('filter done')

        # Use the fixed versions of columns
        df['atype'] = df['atypef']
        df['x'] = df['xf']
        df['y'] = df['yf']

        df = split_trip_legs(connection, str(device.uuid), df)
        pc.display('legs split')
        if df is None:
            logger.info('%s: No legs for trip' % str(device))
            return
        with transaction.atomic():
            self.save_trip(device, df, device._default_variants)
        pc.display('trip saved')

    def generate_trips(self, uuid, start_time, end_time, generation_started_at=None):
        device: Device = Device.objects.filter(uuid=uuid).first()
        if device is None:
            raise GeneratorError('Device %s not found' % uuid)

        sentry_sdk.set_tag('uuid', uuid)
        device._default_variants = {x.mode: x.variant for x in device.default_mode_variants.all()}

        pc = PerfCounter('update trips for %s' % uuid, show_time_to_last=True)
        df = read_locations(connection, uuid, start_time=start_time, end_time=end_time)
        if df is None or not len(df):
            if generation_started_at is not None:
                device.last_processed_data_received_at = generation_started_at
                device.save(update_fields=['last_processed_data_received_at'])
            return
        pc.display('read done, got %d rows' % len(df))

        for trip_id in df.trip_id.unique():
            trip_df = df[df.trip_id == trip_id].copy()
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag('start_time', trip_df.time.min().isoformat())
                scope.set_tag('end_time', trip_df.time.max().isoformat())
                self.process_trip(device, trip_df)
                scope.clear()

        if generation_started_at is not None:
            device.last_processed_data_received_at = generation_started_at
            device.save(update_fields=['last_processed_data_received_at'])
        transaction.commit()
        pc.display('trips generated')
        sentry_sdk.set_tag('uuid', None)

    def find_uuids_with_new_samples(self, min_received_at: Optional[datetime]=None):
        if not min_received_at:
            min_received_at = timezone.now() - timedelta(days=7)

        uuid_qs = (
            Location.objects
            .filter(deleted_at__isnull=True, time__gte=min_received_at)
            .values('uuid').annotate(newest_created_at=Max('created_at')).order_by()
        )
        uuids = uuid_qs.values('uuid')
        devices = (
            Device.objects.annotate(
                last_leg_received_at=Max('trips__legs__received_at'),
                last_leg_end_time=Max('trips__legs__end_time'),
            )
            .values('uuid', 'last_leg_received_at', 'last_leg_end_time', 'last_processed_data_received_at')
            .filter(uuid__in=uuids)
        )
        dev_by_uuid = {
            x['uuid']: dict(
                last_leg_received_at=x['last_leg_received_at'],
                last_leg_end_time=x['last_leg_end_time'],
                last_data_processed_at=x['last_processed_data_received_at'],
            )
            for x in devices
        }

        uuids = uuid_qs.values('uuid', 'newest_created_at')

        uuids_to_process = []
        for row in uuids:
            uuid = row['uuid']
            newest_created_at = row['newest_created_at']

            dev = dev_by_uuid.get(uuid)
            end_time = min_received_at
            if dev:
                if dev['last_leg_received_at'] and newest_created_at <= dev['last_leg_received_at']:
                    continue
                if dev['last_data_processed_at'] and newest_created_at <= dev['last_data_processed_at']:
                    continue
                if dev['last_leg_end_time'] and dev['last_leg_end_time'] > min_received_at:
                    end_time = dev['last_leg_end_time']

            uuids_to_process.append([uuid, end_time])

        return uuids_to_process

    def generate_new_trips(self, only_uuid=None):
        now = timezone.now()
        uuids = self.find_uuids_with_new_samples()
        for uuid, last_leg_end in uuids:
            if only_uuid is not None:
                if str(uuid) != only_uuid:
                    continue
            if last_leg_end:
                start_time = last_leg_end
                end_time = now
            else:
                start_time = None
                end_time = None

            try:
                self.generate_trips(uuid, start_time=start_time, end_time=end_time, generation_started_at=now)
            except GeneratorError as e:
                sentry_sdk.capture_exception(e)

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
