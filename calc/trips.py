import pandas as pd
from utils.perf import PerfCounter


TABLE_NAME = 'trips_ingest_location'
TRANSIT_TABLE = 'transitrt_vehiclelocation'
LOCAL_TZ = 'Europe/Helsinki'
MINS_BETWEEN_TRIPS = 20
DAYS_TO_FETCH = 30
LOCAL_2D_CRS = 3857


def read_trips(eng, uid, start_at=None, end_at=None):
    print('Selected UID %s. Reading dataframe.' % uid)
    pc = PerfCounter('read_locations', show_time_to_last=True)
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
            l.heading
        FROM
            {TABLE_NAME} AS l
        WHERE
            l.uuid = '%s'::uuid
            AND l.time >= now() - interval '{DAYS_TO_FETCH} days'
            AND l.loc_error >= 0
        ORDER BY
            l.time
    """ % uid

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

    with eng.connect() as conn:
        pc.display('connected')
        df = pd.read_sql_query(query, conn)
    pc.display('queried')

    df['timediff'] = df['time'].diff().dt.total_seconds().fillna(value=0)
    df['new_trip'] = df['timediff'] > 20 * 60
    df['trip_id'] = df['new_trip'].cumsum()
    d = ((df.x - df.x.shift()) ** 2 + (df.y - df.y.shift()) ** 2).pow(.5).fillna(0)
    df['distance'] = d

    # Drop trips that do not have enough location samples
    trips = df[df.loc_error < 100].groupby('trip_id')['time'].count()
    trips_to_keep = trips.index[trips > 50]
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


def read_uuids_from_sql(eng):
    with eng.connect() as conn:
        print('Reading uids')
        res = conn.execute(f"""
            SELECT uuid, count(time) AS count FROM {TABLE_NAME}
                WHERE aconf IS NOT NULL AND time >= now() - interval '{DAYS_TO_FETCH} days'
                GROUP BY uuid
                ORDER BY count
                DESC LIMIT 1000
        """)
        rows = res.fetchall()
    uuid_counts = ['%s,%s' % (str(row[0]), row[1]) for row in rows]
    return uuid_counts


def read_uuids(eng):
    try:
        uuids = [x.split(',')[0].strip() for x in open('uuids.txt', 'r').readlines()]
    except FileNotFoundError:
        s = read_uuids_from_sql(eng)
        open('uuids.txt', 'w').write('\n'.join(s))
        uuids = [x.split(',')[0].strip() for x in s]
    return uuids


def split_trip_legs(df):
    df['atype_changed'] = df.atype.ne(df.atype.shift()) | df.trip_id.ne(df.trip_id.shift())
    df['leg_id'] = df['atype_changed'].cumsum()

    leg_locations = df[df.loc_error < 100].groupby('leg_id')['time'].count()
    legs_to_keep = leg_locations.index[leg_locations > 10]
    df = df[df.leg_id.isin(legs_to_keep)]
    df = df.drop(columns=['atype_changed'])
    df = df[~df.atype.isin(['still', 'unknown'])]

    d = ((df.x - df.x.shift()) ** 2 + (df.y - df.y.shift()) ** 2).pow(.5).fillna(0)
    df['distance'] = d

    return df


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv()
    eng = create_engine(os.getenv('DATABASE_URL'))
    default_uid = os.getenv('DEFAULT_UUID')
    if True:
        for uid in read_uuids(eng):
            df = read_trips(eng, uid)
    split_trip_legs(df)
