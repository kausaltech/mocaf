import uuid

import os; import django; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mocaf.settings"); django.setup()  # noqa
from calc.trips import LOCAL_2D_CRS, LOCAL_TZ
from utils.perf import PerfCounter
from django.db import transaction, connection
from django.db.models import Q
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import Point
from psycopg2.extras import execute_values
from trips.models import Device, TransportMode, Trip, Leg, LegLocation


transport_modes = {x.identifier: x for x in TransportMode.objects.all()}
ATYPE_TO_MODE = {
    'walking': transport_modes['walk'],
    'on_foot': transport_modes['walk'],
    'in_vehicle': transport_modes['car'],
    'running': transport_modes['walk'],
    'on_bicycle': transport_modes['bicycle'],
}


LEG_LOCATION_TABLE = LegLocation._meta.db_table

local_crs = SpatialReference(LOCAL_2D_CRS)
gps_crs = SpatialReference(4326)
coord_transform = CoordTransform(local_crs, gps_crs)


def insert_leg_locations(rows):
    pc = PerfCounter('save_locations', show_time_to_last=True)
    query = f'''EXPLAIN ANALYZE INSERT INTO {LEG_LOCATION_TABLE} (leg_id, loc, time, speed) VALUES %s'''

    with connection.cursor() as cursor:
        pc.display('after cursor')
        value_template = f"""(
                %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                %s :: timestamptz,
                %s
        )"""
        ret = execute_values(
            cursor, query, rows, template=value_template, fetch=True, page_size=10000
        )
        for row in ret:
            print(row[0])

    pc.display('after insert')


def generate_leg_rows(leg, df):
    rows = df.apply(lambda row: (
        leg.id,
        row['loc'].x, row['loc'].y,
        '%s' % str(row.time),
        row.speed,
    ), axis=1)
    return list(rows.values)


def save_leg(trip, df, last_ts):
    pc = PerfCounter('save_leg', show_time_to_last=True)

    leg_start = df.time.min()
    leg_end = df.time.max()
    leg_length = df.distance.sum()

    # Ensure trips are ordered properly
    assert leg_start >= last_ts and leg_end >= last_ts

    mode = ATYPE_TO_MODE[df.iloc[0].atype]

    leg = Leg(
        trip=trip,
        mode=mode,
        length=df.distance.sum(),
        started_at=leg_start,
        ended_at=leg_end,
        carbon_footprint=leg_length * mode.emission_factor
    )
    leg.save()
    pc.display('after save')

    rows = generate_leg_rows(leg, df)

    return rows, leg_end


def generate_trips_for_uuid(uid, df):
    pc = PerfCounter('generate_trips', show_time_to_last=True)
    if not len(df):
        print('No samples, returning')
        return

    device = Device.objects.filter(uuid=uid).first()
    if not device:
        device = Device(uuid=uid, token=str(uuid.uuid4()))
        device.save()
    else:
        print('%s exists, returning' % uid)
        return

    pc.display('device save')
    df.time = df.time.dt.tz_localize(LOCAL_TZ)
    min_time = df.time.min()
    max_time = df.time.max()

    # Transform to GPS coordinates
    def transform_point(x, y):
        pnt = Point(x, y, srid=LOCAL_2D_CRS)
        pnt.transform(coord_transform)
        return pnt

    df['loc'] = df[['x', 'y']].apply(lambda row: transform_point(row.x, row.y), axis=1)
    pc.display('after crs')

    # Delete trips that overlap with our data
    overlap = Q(ended_at__gte=min_time) & Q(ended_at__lte=max_time)
    overlap |= Q(started_at__gte=min_time) & Q(started_at__lte=max_time)
    legs = Leg.objects.filter(trip__device=device).filter(overlap)
    device.trips.filter(legs__in=legs).delete()
    pc.display('deleted')

    last_ts = df.time.min()

    # Create trips
    trip_ids = df.trip_id.unique()
    all_rows = []
    for trip_id in trip_ids:
        trip = Trip(device=device)
        trip.save()
        pc.display('trip save')

        trip_df = df[df.trip_id == trip_id].copy()
        leg_ids = trip_df.leg_id.unique()
        for leg_id in leg_ids:
            leg_df = trip_df[trip_df.leg_id == leg_id]
            pc.display('before leg save')
            leg_rows, last_ts = save_leg(trip, leg_df, last_ts)
            all_rows += leg_rows
            pc.display('after leg save')

    insert_leg_locations(all_rows)
    pc.display('after leg location insert')


if __name__ == '__main__':
    import os
    from calc.trips import read_trips, read_uuids, split_trip_legs
    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv()
    eng = create_engine(os.getenv('DATABASE_URL'))
    all_uids = read_uuids(eng)
    for uid in all_uids:
        print(uid)
        device = Device.objects.filter(uuid=uid).first()
        if device is not None:
            continue
        df = read_trips(eng, uid)
        df = split_trip_legs(df)
        transaction.set_autocommit(False)
        with transaction.atomic():
            generate_trips_for_uuid(uid, df)
        transaction.commit()
        transaction.set_autocommit(True)
