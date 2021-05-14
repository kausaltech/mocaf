from datetime import datetime, timedelta
import pandas as pd
from utils.perf import PerfCounter

from .dragimm import filter_trajectory, filters as transport_modes


TABLE_NAME = 'trips_ingest_location'
TRANSIT_TABLE = 'transitrt_vehiclelocation'
LOCAL_TZ = 'Europe/Helsinki'

MINS_BETWEEN_TRIPS = 20
MIN_DISTANCE_MOVED_IN_TRIP = 200

DAYS_TO_FETCH = 30
LOCAL_2D_CRS = 3067


def read_trips(conn, uid, start_time=None, end_time=None, include_all=False):
    print('Selected UID %s. Reading dataframe.' % uid)
    pc = PerfCounter('read_locations', show_time_to_last=True)

    params = dict(uuid=uid)
    if start_time and end_time:
        time_filter = 'AND l.time > %(start_time)s AND l.time <= %(end_time)s'
        params['start_time'] = start_time
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
            l.manual_atype,
            l.created_at AS created_at
        FROM
            {TABLE_NAME} AS l
        WHERE
            l.uuid = %(uuid)s::uuid
            {time_filter}
            AND l.loc_error >= 0
        ORDER BY
            l.time
    """

    '''
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
    pc.display('queried')

    df['time'] = pd.to_datetime(df.time, utc=True)
    df['timediff'] = df['time'].diff().dt.total_seconds().fillna(value=0)
    df['new_trip'] = df['timediff'] > MINS_BETWEEN_TRIPS * 60
    df['trip_id'] = df['new_trip'].cumsum()
    d = ((df.x - df.x.shift()) ** 2 + (df.y - df.y.shift()) ** 2).pow(.5).fillna(0)
    df['distance'] = d

    # Filter out the latest burst of samples, because a trip might
    # still be ongoing
    df = df[df.created_at < df.created_at.max()]

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

    if not include_all:
        df = df[df.trip_id.isin(trips_to_keep)]

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


def split_trip_legs(conn, df):
    df['atype_changed'] = df.atype.ne(df.atype.shift()) | df.trip_id.ne(df.trip_id.shift())
    df['leg_id'] = df['atype_changed'].cumsum()

    s = df['time'].dt.tz_convert(None) - pd.Timestamp('1970-01-01')
    df['epoch_ts'] = s / pd.Timedelta('1s')

    leg_locations = df[df.loc_error < 100].groupby('leg_id')['time'].count()
    legs_to_keep = leg_locations.index[leg_locations > 10]
    df = df[df.leg_id.isin(legs_to_keep)]
    df = df.drop(columns=['atype_changed'])
    df = df[~df.atype.isin(['still', 'unknown'])]

    d = ((df.x - df.x.shift()) ** 2 + (df.y - df.y.shift()) ** 2).pow(.5).fillna(0)
    df['distance'] = d

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

    if False:
        pd.set_option("max_rows", None)
        pd.set_option("min_rows", None)
        df = read_trips(eng, default_uid)
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
