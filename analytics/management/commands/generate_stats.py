import csv
from datetime import date, timedelta, datetime, time
from django.core.management.base import BaseCommand
from django.db.models import Prefetch
from django.db import connection
from analytics.models import Area
from django.conf import settings

from trips.models import Trip, Leg, TransportMode, LOCAL_TZ
from analytics.models import TripSummary


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


def get_daily_od():
    query = """
        SELECT
            (SELECT area.name FROM analytics_area area WHERE ST_Contains(area.geometry, t.start_loc)) AS origin,
            (SELECT area.name FROM analytics_area area WHERE ST_Contains(area.geometry, t.end_loc)) AS dest,
            (SELECT tm.identifier FROM trips_transportmode tm WHERE tm.id = t.primary_mode_id) AS mode,
            COUNT(*) AS trips
        FROM
            analytics_tripsummary t
        WHERE
            t.start_time >= %(start_time)s AND
            t.end_time <= %(end_time)s
        GROUP BY
            origin, dest, mode
    """

    start_date = date(2021, 6, 1)
    end_date = date.today()
    cursor = connection.cursor()
    f = open('od.csv', 'w')
    out = csv.writer(f)
    out.writerow(['date', 'origin', 'dest', 'mode', 'trips'])
    modes = list(TransportMode.objects.all())
    while start_date < end_date:
        print(start_date)
        start_time = LOCAL_TZ.localize(datetime.combine(start_date, time(0)))
        trips = Trip.objects.started_during(start_time, start_time + timedelta(days=1))\
            .filter(summary__isnull=True)\
            .prefetch_related(
                Prefetch('legs', queryset=Leg.objects.active().order_by('start_time'))
            )

        print('Generating for %d trips' % len(trips))
        for trip in trips:
            trip._ordered_legs = list(trip.legs.all())
            obj = TripSummary.from_trip(trip, modes)
            obj.save()

        cursor.execute(query, params=dict(
            start_time=start_time,
            end_time=start_date + timedelta(days=1))
        )
        rows = cursor.fetchall()
        for row in rows:
            out.writerow([start_date.isoformat()] + list(row))

        start_date += timedelta(days=1)


class Command(BaseCommand):
    help = 'Generate statistics'

    def add_arguments(self, parser):
        parser.add_argument('--lengths', action='store_true')
        parser.add_argument('--od', action='store_true')

    def handle(self, *args, **options):
        if options['lengths']:
            get_daily_area_lengths()
        if options['od']:
            get_daily_od()
