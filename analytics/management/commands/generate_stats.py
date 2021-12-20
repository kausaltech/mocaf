import hashlib
import random
import csv

from datetime import date, timedelta, datetime, time
from typing import Optional
import dateutil.parser
from django.core.management.base import BaseCommand
from django.db.models import Prefetch, Sum
from django.db import connection
from django.db.models.query_utils import Q
from analytics.models import Area, DailyModeSummary, DailyTripSummary
from django.conf import settings

from trips.models import Trip, Leg, TransportMode, LOCAL_TZ
from analytics.models import TripSummary, AreaType


LEG_TABLE = 'trips_leg'
LOC_TABLE = 'trips_leglocation'
LOCAL_SRS = settings.LOCAL_SRS


def get_daily_area_lengths(area_type, start_date: Optional[date] = None, end_date: Optional[date] = None):
    cursor = connection.cursor()
    sql = f"""
        WITH day_legs AS (
            SELECT
                mode_id,
                trip_id,
                ST_Transform(
                    (SELECT ST_MakeLine(loc ORDER BY time) FROM {LOC_TABLE} WHERE {LOC_TABLE}.leg_id = {LEG_TABLE}.id),
                    {LOCAL_SRS}
                ) AS line
            FROM {LEG_TABLE}
            WHERE
                start_time >= %(start_time)s AND
                end_time <= %(end_time)s
        )
        SELECT
            area.id,
            day_legs.mode_id,
            SUM(ST_Length(ST_Intersection(area.geometry, day_legs.line))) AS length,
            COUNT(DISTINCT day_legs.trip_id) AS trips
        FROM
            day_legs,
            analytics_area area
        WHERE
            area.type_id = %(area_type)s
            AND ST_Intersects(area.geometry, day_legs.line)
        GROUP BY
            area.id,
            day_legs.mode_id
        ORDER BY
            length DESC
    """

    areas_by_id = {area.id: area for area in area_type.areas.all()}
    modes_by_id = {mode.id: mode for mode in TransportMode.objects.all()}

    if start_date is None:
        start_date = date(2021, 6, 1)
    if end_date is None:
        end_date = date.today() - timedelta(days=1)

    # f = open('lengths.csv', 'w')
    # out = csv.writer(f)
    while start_date < end_date:
        cursor.execute(sql, params=dict(
            start_time=start_date.isoformat(),
            end_time=start_date + timedelta(days=1),
            area_type=area_type.id
        ))
        rows = cursor.fetchall()
        print('%s: %d rows' % (start_date, len(rows)))
        DailyModeSummary.objects.filter(date=start_date, area__type=area_type).delete()
        objs = []
        for row in rows:
            if not row[2]:
                continue
            """
            out.writerow([
                start_date.isoformat(),
                areas_by_id[row[0]].name,
                modes_by_id[row[1]].name,
                row[2]
            ])
            """
            obj = DailyModeSummary(date=start_date)
            obj.area_id = row[0]
            obj.mode_id = row[1]
            obj.length = row[2]
            obj.trips = row[3]
            objs.append(obj)
        DailyModeSummary.objects.bulk_create(objs)
        start_date += timedelta(days=1)


def _generate_summaries(area_type: AreaType, start_date: date, modes: list[TransportMode]):
    start_time = LOCAL_TZ.localize(datetime.combine(start_date, time(0)))
    trips = Trip.objects.started_during(start_time, start_time + timedelta(days=1))\
        .filter(summary__isnull=True)\
        .prefetch_related(
            Prefetch('legs', queryset=Leg.objects.active().order_by('start_time'))
        )
    if len(trips):
        print('Generating summaries for %d trips' % len(trips))
        for trip in trips:
            trip._ordered_legs = list(trip.legs.all())
            obj = TripSummary.from_trip(trip, modes)
            obj.save()


def get_daily_od(area_type: AreaType, start_date: Optional[date] = None, end_date: Optional[date] = None):
    tz = str(LOCAL_TZ)

    if not area_type.is_poi:
        origin_cond = "AND origin.type_id = %(area_type)s"
        dest_cond = "AND dest.type_id = %(area_type)s"
        where_cond = ""
    else:
        origin_cond = ""
        dest_cond = ""
        where_cond = """
            AND (
                (origin.type_id = %(area_type)s AND (dest.type_id != %(area_type)s OR dest.id IS NULL))
                OR (dest.type_id = %(area_type)s AND (origin.type_id != %(area_type)s OR origin.id IS NULL))
            )
        """

    query = f"""
        INSERT INTO analytics_dailytripsummary (date, origin_id, dest_id, mode_id, trips)
        SELECT
            %(date)s AS date,
            origin.id AS origin_id,
            dest.id AS dest_id,
            t.primary_mode_id AS mode_id,
            COUNT(*) AS trips
        FROM
            analytics_tripsummary t
        LEFT OUTER JOIN analytics_area origin
            ON ST_Contains(origin.geometry, t.start_loc) {origin_cond}
        LEFT OUTER JOIN analytics_area dest
            ON ST_Contains(dest.geometry, t.end_loc) {dest_cond}
        WHERE
            t.start_time >= (%(date)s :: date + '00:00' :: time) AT TIME ZONE %(tz)s
            AND t.start_time < (%(date)s :: date + '00:00' :: time + interval '1 day') AT TIME ZONE %(tz)s
            {where_cond}
            AND (origin.id IS NOT NULL OR dest.id IS NOT NULL)
        GROUP BY
            origin_id, dest_id, mode_id
        ORDER BY
            origin_id, dest_id, mode_id
    """

    if start_date is None:
        start_date = date(2021, 6, 1)
    if end_date is None:
        end_date = date.today() - timedelta(days=1)
    cursor = connection.cursor()

    modes = list(TransportMode.objects.all())
    while start_date < end_date:
        print(start_date)
        _generate_summaries(area_type, start_date, modes)
        if area_type.is_poi:
            qs = Q(origin__type=area_type) | Q(dest__type=area_type)
        else:
            qs = Q(origin__type=area_type) & (Q(dest__type=area_type) | Q(dest=None))
            qs |= Q(dest__type=area_type) & (Q(origin__type=area_type) | Q(origin=None))
        DailyTripSummary.objects.filter(date=start_date).filter(qs).delete()
        cursor.execute(query, params=dict(
            date=start_date,
            area_type=area_type.id,
            tz=tz,
        ))
        start_date += timedelta(days=1)


def get_daily_device_trips():
    start_date = date(2021, 6, 1)
    end_date = date.today()

    seed = random.randbytes(10)

    def generate_id(uuid):
        b = uuid.bytes + seed
        return hashlib.sha1(b).hexdigest()[0:8]

    f = open('device_daily_trips.csv', 'w')
    out = csv.writer(f)
    out.writerow(['date', 'device', 'mode', 'length', 'carbon_footprint'])

    while start_date < end_date:
        start_time = LOCAL_TZ.localize(datetime.combine(start_date, time(0)))
        end_time = start_time + timedelta(days=1)
        data = Leg.objects.active().filter(start_time__gte=start_time, start_time__lt=end_time)\
            .values('trip__device__uuid', 'mode__identifier').order_by()\
            .annotate(total_length=Sum('length'), total_carbon_footprint=Sum('carbon_footprint'))

        unique_uuids = set()
        unique_ids = set()
        for row in data:
            user_id = generate_id(row['trip__device__uuid'])
            unique_uuids.add(row['trip__device__uuid'])
            unique_ids.add(user_id)
            out.writerow([
                start_date.isoformat(),
                user_id,
                row['mode__identifier'],
                row['total_length'],
                row['total_carbon_footprint'],
            ])

        if len(unique_uuids) != len(unique_ids):
            print('ID collision')

        print('%s: %d' % (start_date.isoformat(), len(unique_uuids)))
        start_date += timedelta(days=1)


class Command(BaseCommand):
    help = 'Generate statistics'

    def add_arguments(self, parser):
        parser.add_argument('--area-type', type=str)
        parser.add_argument('--start-date', type=str)
        parser.add_argument('--end-date', type=str)
        parser.add_argument('--lengths', action='store_true')
        parser.add_argument('--od', action='store_true')
        parser.add_argument('--daily-device-trips', action='store_true')

    def handle(self, *args, **options):
        if options['area_type']:
            area_type = AreaType.objects.get(identifier=options['area_type'])
        else:
            area_type = AreaType.objects.first()
        print(area_type)
        if options['start_date']:
            start_date = dateutil.parser.isoparse(options['start_date']).date()
        else:
            start_date = None
        if options['end_date']:
            end_date = dateutil.parser.isoparse(options['end_date']).date()
        else:
            end_date = None
        if options['lengths']:
            get_daily_area_lengths(area_type, start_date=start_date, end_date=end_date)
        if options['od']:
            get_daily_od(area_type, start_date=start_date, end_date=end_date)
        if options['daily_device_trips']:
            get_daily_device_trips()
