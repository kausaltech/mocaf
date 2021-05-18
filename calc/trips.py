import logging
import numba
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from utils.perf import PerfCounter

from .dragimm import filter_trajectory, filters as transport_modes


TABLE_NAME = 'trips_ingest_location'
TRANSIT_TABLE = 'transitrt_vehiclelocation'
OSM_ROADS_TABLE = 'planet_osm_line'
LOCAL_TZ = 'Europe/Helsinki'

MINS_BETWEEN_TRIPS = 20
MIN_DISTANCE_MOVED_IN_TRIP = 200
MIN_SAMPLES_PER_LEG = 15

DAYS_TO_FETCH = 10
LOCAL_2D_CRS = 3067

logger = logging.getLogger(__name__)


def read_trips(conn, uid, start_time=None, end_time=None, include_all=False):
    pc = PerfCounter('read %s' % uid, show_time_to_last=True)

    params = dict(uuid=uid)
    if start_time:
        time_filter = 'AND l.time > %(start_time)s'
        params['start_time'] = start_time
        if end_time:
            time_filter += ' AND l.time <= %(end_time)s'
            params['end_time'] = end_time
    else:
        # time_filter = f"l.time >= now() - interval '{DAYS_TO_FETCH} days'"
        time_filter = ''

    query = f"""
        SELECT
            l.time AS time,
            -- ST_X(ST_Transform(l.loc, 4326)) AS lon,
            -- ST_Y(ST_Transform(l.loc, 4326)) AS lat,
            ST_X(l.loc) AS x,
            ST_Y(l.loc) AS y,
            l.loc_error,
            l.atype,
            l.aconf,
            l.speed,
            l.heading,
            l.is_moving,
            l.manual_atype,
            l.odometer,
            l.battery_charging,
            cw.closest_car_way_dist,
            cw.closest_car_way_name,
            l.created_at AS created_at
        FROM
            {TABLE_NAME} AS l
        LEFT JOIN LATERAL (
            SELECT
                name AS closest_car_way_name,
                ST_Distance(w.way, l.loc) AS closest_car_way_dist
                FROM planet_osm_line AS w
                WHERE
                    highway IN (
                        'minor', 'road', 'unclassified', 'residential', 'tertiary_link', 'tertiary',
                        'secondary_link', 'secondary', 'primary_link', 'primary', 'trunk_link',
                        'trunk', 'motorway_link', 'motorway',
                        'service'
                    )
                    AND w.way && ST_Expand(l.loc, 50)
                ORDER BY ST_Distance(w.way, l.loc) ASC
                LIMIT 1
        ) AS cw ON true
        WHERE
            l.uuid = %(uuid)s::uuid
            {time_filter}
            AND l.loc_error >= 0
        ORDER BY
            l.time
    """

    '''
        LEFT JOIN LATERAL (
            SELECT
                (SELECT trip_headsign FROM gtfs.trips
                    WHERE gtfs.trips.shape_id = g.shape_id LIMIT 1
                ),
                ST_Distance(g.the_geom, l.loc) AS closest_transit_line_dist
                FROM gtfs.shape_geoms AS g
                WHERE
                    g.the_geom && ST_Expand(l.loc, 100)
                ORDER BY ST_Distance(g.the_geom, l.loc) ASC
                LIMIT 1
        ) AS transit ON true
    query = f"""
        SELECT
            l.time AS time,
            --ST_X(ST_Transform(l.loc, 4326)) AS lon,
            --ST_Y(ST_Transform(l.loc, 4326)) AS lat,
            --ST_X(ST_Transform(l.loc, {LOCAL_2D_CRS})) AS x,
            --ST_Y(ST_Transform(l.loc, {LOCAL_2D_CRS})) AS y,
            l.loc_error,
            l.atype,
            l.aconf,
            l.speed,
            l.heading,
            cv.vehicle_ref,
            cv.journey_ref,
            cv.timediff,
            cv.dist
        FROM
            {TABLE_NAME} AS l
        LEFT JOIN LATERAL (
            SELECT
                vehicle_ref,
                journey_ref,
                EXTRACT(EPOCH FROM l.time - v.time) AS timediff,
                ST_Distance(v.loc, l.loc) AS dist
                FROM {TRANSIT_TABLE} AS v
                WHERE
                    abs(EXTRACT(EPOCH FROM l.time - v.time)) < 10
                    AND ST_DWithin(v.loc, l.loc, 100)
                ORDER BY v.loc <-> l.loc
                LIMIT 1
        ) AS cv ON true
        WHERE
            l.uuid = '%s'::uuid
            -- AND l.time >= now() - interval '{DAYS_TO_FETCH} days'
            AND l.time >= '2021-02-15'
            -- AND l.time <= '2021-02-16'
            AND l.loc_error >= 0
        ORDER BY
            l.time
    """ % uid
    '''

    df = pd.read_sql_query(query, conn, params=params)
    pc.display('queried, got %d rows' % len(df))

    df['time'] = pd.to_datetime(df.time, utc=True)
    df['timediff'] = df['time'].diff().dt.total_seconds().fillna(value=0)
    df['new_trip'] = df['timediff'] > MINS_BETWEEN_TRIPS * 60
    df['trip_id'] = df['new_trip'].cumsum()
    d = ((df.x - df.x.shift()) ** 2 + (df.y - df.y.shift()) ** 2).pow(.5).fillna(0)
    df['distance'] = d

    # Filter out everything after the latest "not moving" event,
    # because a trip might still be ongoing
    if not include_all:
        not_moving = df[df.is_moving == False]
        if not len(not_moving):
            # If we don't have any "not moving" samples, just filter
            # out the last burst.
            df = df[df.created_at < df.created_at.max()]
        else:
            last_not_moving = not_moving.time.max()
            df = df[df.time <= last_not_moving]

    # Filter out trips that do not have enough low location error samples
    # far enough from the trip center point.
    good_samples = df[df.loc_error < 100]
    if not len(good_samples):
        print('No good samples, returning')
        return

    avg_loc = good_samples.groupby('trip_id')[['x', 'y']].mean()
    avg_loc.columns = ['avg_x', 'avg_y']
    d = good_samples.join(avg_loc, on='trip_id')
    d['mean_distance'] = ((d.x - d.avg_x) ** 2 + (d.y - d.avg_y) ** 2).pow(.5)

    loc_count = d[d['mean_distance'] > MIN_DISTANCE_MOVED_IN_TRIP].groupby('trip_id')['time'].count()
    trips_to_keep = loc_count.index[loc_count > 10]

    df.loc[~df.trip_id.isin(trips_to_keep), 'trip_id'] = -1

    if not include_all:
        df = df[df.trip_id >= 0]

    df = df.drop(columns=['timediff', 'new_trip'])

    '''
    for trip_id in trips_to_keep:
        print(trip_id)
        tdf = df[df.trip_id == trip_id]
        min_time = tdf.time.min()
        max_time = tdf.time.max()
        query = f"""
            SELECT
                l.time AT TIME ZONE '{LOCAL_TZ}' AS time,
                cv.vehicle_ref,
                cv.journey_ref,
                cv.timediff,
                cv.dist
            FROM
                {TABLE_NAME} AS l
            CROSS JOIN LATERAL
                (SELECT
                    vehicle_ref,
                    journey_ref,
                    EXTRACT(EPOCH FROM l.time - v.time) AS timediff,
                    ST_Distance(v.loc, l.loc) AS dist
                    FROM {TRANSIT_TABLE} AS v
                    WHERE
                        v.time >= %(min_time)s AND v.time <= %(max_time)s
                        AND abs(EXTRACT(EPOCH FROM l.time - v.time)) < 10
                        AND ST_DWithin(v.loc, l.loc, 100)
                    ORDER BY ST_Distance(v.loc, l.loc)
                    LIMIT 1
                ) AS cv
            WHERE
                l.uuid = %(uid)s::uuid
                AND l.time >= %(min_time)s AND l.time <= %(max_time)s
            ORDER BY l.time
        """

        print('querying')
        with eng.connect() as conn:
            vdf = pd.read_sql_query(query, conn, params=dict(
                min_time=min_time,
                max_time=max_time,
                uid=uid,
            ))
        if len(vdf):
            pd.set_option("max_rows", 100)
            pd.set_option("min_rows", 100)
            print(tdf)
            print(vdf)
        '''

    return df


ATYPE_MAPPING = {
    'still': 'still',
    'running': 'walking',
    'on_foot': 'walking',
    'walking': 'walking',
    'on_bicycle': 'cycling',
    'in_vehicle': 'driving',
    'unknown': None,
}
ATYPE_REVERSE = {
    'still': 'still',
    'walking': 'on_foot',
    'cycling': 'on_bicycle',
    'driving': 'in_vehicle',
}
ALL_ATYPES = [
    'still', 'on_foot', 'on_bicycle', 'in_vehicle', 'car', 'bus', 'tram', 'train', 'other', 'unknown',
]
ATYPE_STILL = ALL_ATYPES.index('still')
ATYPE_UNKNOWN = ALL_ATYPES.index('unknown')

IDX_MAPPING = {idx: ATYPE_REVERSE[x] for idx, x in enumerate(transport_modes.keys())}


def filter_trips(df):
    out = df[['time', 'x', 'y', 'speed']].copy()
    s = df['time'].dt.tz_convert(None) - pd.Timestamp('1970-01-01')
    out['time'] = s / pd.Timedelta('1s')

    out['location_std'] = df['loc_error'].clip(lower=0.1)
    out['atype'] = df['atype'].map(ATYPE_MAPPING)
    out['aconf'] = df['aconf'] / 100
    out.loc[out.aconf == 1, 'aconf'] /= 2

    ms, Ss, state_probs, most_likely_path, _ = filter_trajectory((r for i, r in out.iterrows()))

    x = ms[:, 0]
    y = ms[:, 1]
    df = df.copy()
    df['xf'] = x
    df['yf'] = y
    df['atypef'] = most_likely_path
    df['atypef'] = df['atypef'].map(IDX_MAPPING)

    modes = transport_modes.keys()
    for idx, mode in enumerate(modes):
        if mode == 'driving':
            mode = 'in_vehicle'
        elif mode == 'cycling':
            mode = 'on_bicycle'
        df[mode] = [x[idx] for x in state_probs]

    return df


def read_uuids_from_sql(conn):
    print('Reading uids')
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT uuid, count(time) AS count FROM {TABLE_NAME}
                WHERE aconf IS NOT NULL AND time >= now() - interval '{DAYS_TO_FETCH} days'
                GROUP BY uuid
                ORDER BY count
                DESC LIMIT 1000
        """)
        rows = cursor.fetchall()
    uuid_counts = ['%s,%s' % (str(row[0]), row[1]) for row in rows]
    return uuid_counts


def read_uuids(conn):
    try:
        uuids = [x.split(',')[0].strip() for x in open('uuids.txt', 'r').readlines()]
    except FileNotFoundError:
        s = read_uuids_from_sql(conn)
        open('uuids.txt', 'w').write('\n'.join(s))
        uuids = [x.split(',')[0].strip() for x in s]
    return uuids


def get_vehicle_locations(conn, start: datetime, end: datetime):
    query = """
        SELECT
            vehicle_ref,
            journey_ref,
            extract(epoch from time) as time,
            ST_X(loc) AS x,
            ST_Y(loc) AS y,
            (SELECT long_name FROM route WHERE id = transitrt_vehiclelocation.route_id) AS route_name
        FROM transitrt_vehiclelocation
        WHERE time >= %(start)s - interval '5 minutes' AND time <= %(end)s + interval '5 minutes'
        ORDER BY time
    """
    params = dict(start=start, end=end)
    df = pd.read_sql_query(query, conn, params=params)
    return df


@numba.njit(cache=True)
def filter_legs(time, x, y, atype, distance, loc_error, speed):
    n_rows = len(time)

    last_atype_start = 0
    atype_count = 0
    atype_counts = np.zeros(n_rows, dtype='int64')
    leg_ids = np.zeros(n_rows, dtype='int64')

    # First calculate how long same atype stretches we have
    for i in range(1, n_rows):
        if atype[i] == atype[i - 1]:
            if loc_error[i] < 100:
                atype_count += 1
        else:
            for j in range(last_atype_start, i):
                atype_counts[j] = atype_count
            atype_count = 0
            last_atype_start = i

    max_leg_id = 0
    current_leg = -1
    prev = 0
    for i in range(n_rows):
        # If we're in the middle of a trip and we have only a couple of atypes
        # for a different mode, change them to match the others.
        if i > 0 and i < n_rows - MIN_SAMPLES_PER_LEG:
            if atype_counts[i] <= 3 and atype_counts[i - 1] > MIN_SAMPLES_PER_LEG:
                atype[i] = atype[i - 1]
                atype_counts[i] = atype_counts[i - 1]

        if i == 0 or atype[i] != atype[i - 1]:
            if atype_counts[i] >= MIN_SAMPLES_PER_LEG and atype[i] != ATYPE_STILL and atype[i] != ATYPE_UNKNOWN:
                # Enough good samples in this leg? We'll keep it.
                if i > 0:
                    max_leg_id += 1
                current_leg = max_leg_id
                distance[i] = 0
                prev = i
            else:
                # Not enough? Amputation.
                current_leg = -1
            leg_ids[i] = current_leg
            continue
        elif current_leg == -1 or loc_error[i] > 100 or atype[i] == ATYPE_STILL or atype[i] == ATYPE_UNKNOWN:
            leg_ids[i] = -1
            continue

        dist = ((x[prev] - x[i]) ** 2 + (y[prev] - y[i]) ** 2) ** 0.5
        timediff = time[i] - time[prev]
        calc_speed = dist / timediff

        # If the speed based on (x, y) differs too much from speeds reported by GPS,
        # drop the previous sample as invalid.
        if not np.isnan(speed[i]) and abs(calc_speed - speed[i]) > 30:
            leg_ids[i - 1] = -1
            distance[i] = 0
        else:
            distance[i] = dist
        leg_ids[i] = current_leg
        prev = i

    return leg_ids


def split_trip_legs(conn, df, include_all=False):
    assert len(df.trip_id.unique()) == 1
    s = df['time'].dt.tz_convert(None) - pd.Timestamp('1970-01-01')
    df['epoch_ts'] = s / pd.Timedelta('1s')
    df['calc_speed'] = df.speed
    df['int_atype'] = df.atype.map(ALL_ATYPES.index).astype(int)
    df['leg_id'] = filter_legs(
        time=df.epoch_ts.to_numpy(), x=df.x.to_numpy(), y=df.y.to_numpy(), atype=df.int_atype.to_numpy(),
        distance=df.distance.to_numpy(), loc_error=df.loc_error.to_numpy(), speed=df.speed.to_numpy()
    )
    df.atype = df.int_atype.map(lambda x: ALL_ATYPES[x])

    if False:
        pd.set_option("max_rows", None)
        pd.set_option("min_rows", None)
        print(df.set_index(df.time.dt.tz_convert(LOCAL_TZ)).drop(columns=['time']))

    if not include_all:
        df = df[df.leg_id != -1]
    if not len(df):
        return None

    df = df.drop(columns=['epoch_ts', 'calc_speed', 'int_atype'])

    """
    for leg in df.leg_id.unique():
        leg_df = df[df.leg_id == leg]
        if leg_df.iloc[0].atype != 'in_vehicle':
            continue

        transit_locs = get_vehicle_locations(conn, leg_df.time.min(), leg_df.time.max())
        transit_loc_by_id = {vech: d for vech, d in transit_locs.groupby('vehicle_ref')}
        print(leg_df)
        out = transit_likelihoods(leg_df, transit_loc_by_id)
        transit_df = pd.DataFrame(out.items(), columns=['vehicle_ref', 'dist']).dropna().sort_values('dist')

        print(transit_df)
        closest = transit_df.iloc[-1]
        print(transit_locs[transit_locs.vehicle_ref == closest.vehicle_ref].iloc[0])
    """

    return df


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv()
    eng = create_engine(os.getenv('DATABASE_URL'))
    default_uid = os.getenv('DEFAULT_UUID')

    if False:
        start = datetime(2021, 4, 28, 12)
        end = start + timedelta(hours=1)
        out = get_vehicle_locations(eng, start, end)
        exit()

    if True:
        from dateutil.parser import parse
        pd.set_option("max_rows", None)
        pd.set_option("min_rows", None)
        df = read_trips(
            eng.connect().connection, default_uid,
            start_time=parse('2021-05-17T08:00+03:00'),
            end_time=parse('2021-05-17T09:00+03:00'),
        )
        trip_ids = df.trip_id.unique()
        for trip in trip_ids:
            print(trip)
            tdf = filter_trips(df[df.trip_id == trip])

    if True:
        for uid in read_uuids(eng):
            df = read_trips(eng, uid)
            print(df)
            exit()
    # split_trip_legs(df)
