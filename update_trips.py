import uuid
import geopandas as gpd

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
    query = f'''INSERT INTO {LEG_LOCATION_TABLE} (
        leg_id, loc, time, speed
    ) VALUES %s'''

    with connection.cursor() as cursor:
        pc.display('after cursor')
        value_template = f"""(
                %s,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                %s :: timestamptz,
                %s
        )"""
        execute_values(
            cursor, query, rows, template=value_template, page_size=10000
        )

    pc.display('after insert')


# Transform to GPS coordinates
def make_point(x, y):
    pnt = Point(x, y, srid=LOCAL_2D_CRS)
    pnt.transform(coord_transform)
    return pnt


def generate_leg_rows(leg, df):
    rows = df.apply(lambda row: (
        leg.id,
        row.lon, row.lat,
        '%s' % str(row.time),
        row.speed,
    ), axis=1)
    return list(rows.values)


def save_leg(trip, df, last_ts):
    start = df.iloc[0][['time', 'x', 'y']]
    end = df.iloc[-1][['time', 'x', 'y']]

    leg_length = df['distance'].sum()

    # Ensure trips are ordered properly
    assert start.time >= last_ts and end.time >= last_ts

    mode = ATYPE_TO_MODE[df.iloc[0].atype]

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

    rows = generate_leg_rows(leg, df)

    return rows, end.time


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

    min_time = df.time.min()
    max_time = df.time.max()

    df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y, crs=LOCAL_2D_CRS))
    pc.display('after crs for %d points' % len(df))
    df['geometry'] = df['geometry'].to_crs(4326)
    df['lon'] = df.geometry.x
    df['lat'] = df.geometry.y
    pc.display('after crs for %d points' % len(df))

    # Delete trips that overlap with our data
    overlap = Q(end_time__gte=min_time) & Q(end_time__lte=max_time)
    overlap |= Q(start_time__gte=min_time) & Q(start_time__lte=max_time)
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
            leg_rows, last_ts = save_leg(trip, leg_df, last_ts)
            all_rows += leg_rows

    pc.display('after leg location generation')
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
    transaction.set_autocommit(False)
    for uid in all_uids:
        print(uid)
        device = Device.objects.filter(uuid=uid).first()
        if device is not None:
            continue
        df = read_trips(eng, uid)
        df = split_trip_legs(df)
        with transaction.atomic():
            generate_trips_for_uuid(uid, df)
        transaction.commit()
    transaction.set_autocommit(True)
