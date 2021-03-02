import pandas as pd
from utils.perf import PerfCounter


TABLE_NAME = 'trips_location'
LOCAL_TZ = 'Europe/Helsinki'
MINS_BETWEEN_TRIPS = 20
DAYS_TO_FETCH = 21
LOCAL_2D_CRS = 3067


def read_trips(eng, uid):
    print('Selected UID %s. Reading dataframe.' % uid)
    pc = PerfCounter('read_locations', show_time_to_last=True)
    query = f"""
        SELECT
            time AT TIME ZONE '{LOCAL_TZ}' AS time,
            ST_X(ST_Transform(loc, 4326)) AS lon,
            ST_Y(ST_Transform(loc, 4326)) AS lat,
            ST_X(ST_Transform(loc, {LOCAL_2D_CRS})) AS x,
            ST_Y(ST_Transform(loc, {LOCAL_2D_CRS})) AS y,
            loc_error,
            atype,
            aconf,
            speed,
            heading
        FROM {TABLE_NAME}
        WHERE
            uuid = '%s'::uuid
            AND time >= now() - interval '{DAYS_TO_FETCH} days'
            AND loc_error >= 0
        ORDER BY time
    """ % uid
    with eng.connect() as conn:
        pc.display('connected')
        df = pd.read_sql_query(query, conn)
    pc.display('queried')

    df['timediff'] = df['time'].diff().dt.total_seconds().fillna(value=0)
    df['new_trip'] = df['timediff'] > 20 * 60
    df['trip_id'] = df['new_trip'].cumsum()

    # Drop trips that do not have enough location samples
    trips = df[df.loc_error < 100].groupby('trip_id')['time'].count()
    trips_to_keep = trips.index[trips > 50]
    df = df[df.trip_id.isin(trips_to_keep)]
    df = df.drop(columns=['timediff', 'new_trip'])

    return df


def read_uuids_from_sql(eng):
    with eng.connect() as conn:
        print('Reading uids')
        res = conn.execute(f"""
            SELECT uuid, count(id) AS count FROM {TABLE_NAME}
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
    print(df)

    return df


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine

    load_dotenv()
    eng = create_engine(os.getenv('DATABASE_URL'))
    df = read_trips(eng, os.getenv('DEFAULT_UUID'))
    split_trip_legs(df)
