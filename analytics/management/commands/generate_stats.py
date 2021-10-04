import csv
from datetime import date, timedelta, datetime, time
from django.core.management.base import BaseCommand
from django.db.models import Prefetch
from django.db import connection
from analytics.models import Area
from django.conf import settings

from trips.models import Trip, Leg, TransportMode, LOCAL_TZ
from analytics.models import TripSummary, AreaType


LEG_TABLE = 'trips_leg'
LOC_TABLE = 'trips_leglocation'
LOCAL_SRS = settings.LOCAL_SRS


def get_daily_area_lengths():
    cursor = connection.cursor()
    sql = f"""
        WITH day_legs AS (
            SELECT
                (SELECT identifier FROM trips_transportmode WHERE id = mode_id) AS mode_id,
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
            area.name,
            day_legs.mode_id,
            SUM(ST_Length(ST_Intersection(area.geometry, day_legs.line))) AS length
        FROM
            day_legs,
            analytics_area area
        GROUP BY
            area.name,
            day_legs.mode_id
        ORDER BY
            length DESC
    """
    start_date = date(2021, 6, 1)
    end_date = date.today()
    f = open('lengths.csv', 'w')
    out = csv.writer(f)
    while start_date < end_date:
        print(start_date)
        cursor.execute(sql, params=dict(start_time=start_date.isoformat(), end_time=start_date + timedelta(days=1)))
        rows = cursor.fetchall()
        for row in rows:
            out.writerow([start_date.isoformat()] + list(row))
        start_date += timedelta(days=1)


def get_daily_od(area_type: AreaType):
    tz = str(LOCAL_TZ)

    query = """
        INSERT INTO analytics_dailytripsummary (date, origin_id, dest_id, mode_id, trips)
        SELECT
            %(date)s AS date,
            (SELECT area.id FROM analytics_area area WHERE
                ST_Contains(area.geometry, t.start_loc)
                AND area.type_id = %(area_type)s
            ) AS origin_id,
            (SELECT area.id FROM analytics_area area WHERE
                ST_Contains(area.geometry, t.end_loc)
                AND area.type_id = %(area_type)s
            ) AS dest_id,
            t.primary_mode_id AS mode_id,
            COUNT(*) AS trips
        FROM
            analytics_tripsummary t
        WHERE
            t.start_time >= (%(date)s :: date + '00:00' :: time) AT TIME ZONE %(tz)s AND
            t.end_time < (%(date)s :: date + '00:00' :: time + interval '1 day') AT TIME ZONE %(tz)s
        GROUP BY
            origin_id, dest_id, mode_id
    """

    start_date = date(2021, 6, 1)
    end_date = date.today()
    cursor = connection.cursor()

    modes = list(TransportMode.objects.all())
    while start_date < end_date:
        print(start_date)
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

        cursor.execute(query, params=dict(
            date=start_date,
            area_type=area_type.id,
            tz=tz,
        ))

        start_date += timedelta(days=1)


class Command(BaseCommand):
    help = 'Generate statistics'

    def add_arguments(self, parser):
        parser.add_argument('--area-type', type=str)
        parser.add_argument('--lengths', action='store_true')
        parser.add_argument('--od', action='store_true')

    def handle(self, *args, **options):
        if options['area_type']:
            area_type = AreaType.objects.get(identifier=options['area_type'])
        else:
            area_type = AreaType.objects.first()
        print(area_type)
        if options['lengths']:
            get_daily_area_lengths()
        if options['od']:
            get_daily_od(area_type)
