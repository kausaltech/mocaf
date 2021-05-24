from django.contrib.gis.db import models
from django.conf import settings


class Agency(models.Model):
    feed_index = models.OneToOneField('FeedInfo', models.CASCADE, db_column='feed_index', primary_key=True)
    agency_id = models.TextField()
    agency_name = models.TextField(blank=True, null=True)
    agency_url = models.TextField(blank=True, null=True)
    agency_timezone = models.TextField(blank=True, null=True)
    agency_lang = models.TextField(blank=True, null=True)
    agency_phone = models.TextField(blank=True, null=True)
    agency_fare_url = models.TextField(blank=True, null=True)
    agency_email = models.TextField(blank=True, null=True)
    bikes_policy_url = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"agency'
        unique_together = (('feed_index', 'agency_id'),)


class Calendar(models.Model):
    feed_index = models.ForeignKey('FeedInfo', models.CASCADE, db_column='feed_index')
    service_id = models.TextField(primary_key=True)
    monday = models.IntegerField()
    tuesday = models.IntegerField()
    wednesday = models.IntegerField()
    thursday = models.IntegerField()
    friday = models.IntegerField()
    saturday = models.IntegerField()
    sunday = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'gtfs\".\"calendar'
        unique_together = (('feed_index', 'service_id'),)


class CalendarDate(models.Model):
    feed_index = models.ForeignKey(Calendar, models.CASCADE, db_column='feed_index')
    service_id = models.TextField(primary_key=True)
    date = models.DateField()
    exception_type = models.ForeignKey('ExceptionType', models.CASCADE, db_column='exception_type', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"calendar_dates'


class ContinuousPickup(models.Model):
    continuous_pickup = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"continuous_pickup'


class ExceptionType(models.Model):
    exception_type = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"exception_types'


class FareAttribute(models.Model):
    feed_index = models.ForeignKey(Agency, models.CASCADE, db_column='feed_index')
    fare_id = models.TextField(primary_key=True)
    price = models.FloatField()
    currency_type = models.TextField()
    payment_method = models.ForeignKey('PaymentMethod', models.CASCADE, db_column='payment_method', blank=True, null=True)
    transfers = models.IntegerField(blank=True, null=True)
    transfer_duration = models.IntegerField(blank=True, null=True)
    agency_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"fare_attributes'
        unique_together = (('feed_index', 'fare_id'),)


class FareRule(models.Model):
    feed_index = models.ForeignKey(Calendar, models.CASCADE, db_column='feed_index')
    fare_id = models.TextField(primary_key=True)
    route_id = models.TextField(blank=True, null=True)
    origin_id = models.TextField(blank=True, null=True)
    destination_id = models.TextField(blank=True, null=True)
    contains_id = models.TextField(blank=True, null=True)
    service_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"fare_rules'


class FeedInfo(models.Model):
    feed_index = models.AutoField(primary_key=True)
    feed_publisher_name = models.TextField(blank=True, null=True)
    feed_publisher_url = models.TextField(blank=True, null=True)
    feed_timezone = models.TextField(blank=True, null=True)
    feed_lang = models.TextField(blank=True, null=True)
    feed_version = models.TextField(blank=True, null=True)
    feed_start_date = models.DateField(blank=True, null=True)
    feed_end_date = models.DateField(blank=True, null=True)
    feed_id = models.TextField(blank=True, null=True)
    feed_contact_url = models.TextField(blank=True, null=True)
    feed_contact_email = models.TextField(blank=True, null=True)
    feed_download_date = models.DateField(blank=True, null=True)
    feed_file = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"feed_info'


class Frequency(models.Model):
    feed_index = models.ForeignKey('FeedInfo', models.CASCADE, db_column='feed_index')
    trip_id = models.TextField(primary_key=True)
    start_time = models.TextField()
    end_time = models.TextField()
    headway_secs = models.IntegerField()
    exact_times = models.IntegerField(blank=True, null=True)
    start_time_seconds = models.IntegerField(blank=True, null=True)
    end_time_seconds = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"frequencies'
        unique_together = (('feed_index', 'trip_id', 'start_time'),)


class LocationType(models.Model):
    location_type = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"location_types'


class PaymentMethod(models.Model):
    payment_method = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"payment_methods'


class PickupDropoffType(models.Model):
    type_id = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"pickup_dropoff_types'


class RouteType(models.Model):
    route_type = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"route_types'


class Route(models.Model):
    feed_index = models.ForeignKey(FeedInfo, models.CASCADE, db_column='feed_index', related_name='routes')
    route_id = models.TextField(primary_key=True)
    agency = models.ForeignKey(Agency, models.CASCADE)
    route_short_name = models.TextField(blank=True, null=True)
    route_long_name = models.TextField(blank=True, null=True)
    route_desc = models.TextField(blank=True, null=True)
    route_type = models.ForeignKey(RouteType, models.CASCADE, db_column='route_type', blank=True, null=True)
    route_url = models.TextField(blank=True, null=True)
    route_color = models.TextField(blank=True, null=True)
    route_text_color = models.TextField(blank=True, null=True)
    route_sort_order = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"routes'
        unique_together = (('feed_index', 'route_id'),)

    def __str__(self):
        return '%s – %s' % (self.route_short_name, self.route_long_name)


class ShapeGeometry(models.Model):
    feed_index = models.ForeignKey(FeedInfo, models.CASCADE, db_column='feed_index')
    shape = models.OneToOneField('Shape', models.CASCADE, primary_key=True)
    length = models.DecimalField(max_digits=12, decimal_places=2)
    the_geom = models.LineStringField(blank=True, null=True, srid=settings.LOCAL_SRS)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"shape_geoms'
        unique_together = (('feed_index', 'shape_id'),)


class Shape(models.Model):
    feed_index = models.ForeignKey(FeedInfo, models.CASCADE, db_column='feed_index')
    shape_id = models.TextField(primary_key=True)
    shape_pt_lat = models.FloatField()
    shape_pt_lon = models.FloatField()
    shape_pt_sequence = models.IntegerField()
    shape_dist_traveled = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"shapes'


class StopTime(models.Model):
    feed_index = models.ForeignKey(FeedInfo, models.CASCADE, db_column='feed_index')
    trip = models.ForeignKey('Trip', models.CASCADE)
    arrival_time = models.DurationField(blank=True, null=True)
    departure_time = models.DurationField(blank=True, null=True)
    stop = models.ForeignKey('Stop', models.SET_NULL, null=True)
    stop_sequence = models.IntegerField()
    stop_headsign = models.TextField(blank=True, null=True)
    pickup_type = models.ForeignKey(
        PickupDropoffType, models.CASCADE, db_column='pickup_type', blank=True, null=True,
        related_name='stop_times_pickup',
    )
    drop_off_type = models.ForeignKey(
        PickupDropoffType, models.CASCADE, db_column='drop_off_type', blank=True, null=True,
        related_name='stop_times_drop_off',
    )
    shape_dist_traveled = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    timepoint = models.ForeignKey('Timepoint', models.CASCADE, db_column='timepoint', blank=True, null=True)
    continuous_drop_off = models.IntegerField(blank=True, null=True)
    continuous_pickup = models.ForeignKey(ContinuousPickup, models.CASCADE, db_column='continuous_pickup', blank=True, null=True)
    arrival_time_seconds = models.IntegerField(blank=True, null=True)
    departure_time_seconds = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"stop_times'
        unique_together = (('feed_index', 'trip_id', 'stop_sequence'),)


class Stop(models.Model):
    feed_index = models.ForeignKey(FeedInfo, models.CASCADE, db_column='feed_index')
    stop_id = models.TextField(primary_key=True)
    stop_name = models.TextField(blank=True, null=True)
    stop_desc = models.TextField(blank=True, null=True)
    stop_lat = models.FloatField(blank=True, null=True)
    stop_lon = models.FloatField(blank=True, null=True)
    zone_id = models.TextField(blank=True, null=True)
    stop_url = models.TextField(blank=True, null=True)
    stop_code = models.TextField(blank=True, null=True)
    stop_street = models.TextField(blank=True, null=True)
    stop_city = models.TextField(blank=True, null=True)
    stop_region = models.TextField(blank=True, null=True)
    stop_postcode = models.TextField(blank=True, null=True)
    stop_country = models.TextField(blank=True, null=True)
    stop_timezone = models.TextField(blank=True, null=True)
    direction = models.TextField(blank=True, null=True)
    position = models.TextField(blank=True, null=True)
    parent_station = models.TextField(blank=True, null=True)
    wheelchair_boarding = models.ForeignKey('WheelchairBoarding', models.CASCADE, db_column='wheelchair_boarding', blank=True, null=True)
    wheelchair_accessible = models.ForeignKey('WheelchairAccessible', models.CASCADE, db_column='wheelchair_accessible', blank=True, null=True)
    location_type = models.ForeignKey(LocationType, models.CASCADE, db_column='location_type', blank=True, null=True)
    vehicle_type = models.IntegerField(blank=True, null=True)
    platform_code = models.TextField(blank=True, null=True)
    the_geom = models.PointField(blank=True, null=True, srid=settings.LOCAL_SRS)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"stops'
        unique_together = (('feed_index', 'stop_id'),)

    def __str__(self):
        return '%s – %s' % (self.stop_code, self.stop_name)


class Timepoint(models.Model):
    timepoint = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"timepoints'


class TransferType(models.Model):
    transfer_type = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"transfer_types'


class Transfer(models.Model):
    feed_index = models.IntegerField(primary_key=True)
    from_stop_id = models.TextField(blank=True, null=True)
    to_stop_id = models.TextField(blank=True, null=True)
    transfer_type = models.ForeignKey(TransferType, models.CASCADE, db_column='transfer_type', blank=True, null=True)
    min_transfer_time = models.IntegerField(blank=True, null=True)
    from_route_id = models.TextField(blank=True, null=True)
    to_route_id = models.TextField(blank=True, null=True)
    service_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"transfers'


class Trip(models.Model):
    feed_index = models.ForeignKey(FeedInfo, models.CASCADE, db_column='feed_index')
    route_id = models.ForeignKey(Route, models.CASCADE)
    service_id = models.TextField()
    trip_id = models.TextField(primary_key=True)
    trip_headsign = models.TextField(blank=True, null=True)
    direction_id = models.IntegerField(blank=True, null=True)
    block_id = models.TextField(blank=True, null=True)
    shape_id = models.TextField(blank=True, null=True)
    trip_short_name = models.TextField(blank=True, null=True)
    wheelchair_accessible = models.ForeignKey('WheelchairAccessible', models.CASCADE, db_column='wheelchair_accessible', blank=True, null=True)
    direction = models.TextField(blank=True, null=True)
    schd_trip_id = models.TextField(blank=True, null=True)
    trip_type = models.TextField(blank=True, null=True)
    exceptional = models.IntegerField(blank=True, null=True)
    bikes_allowed = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"trips'
        unique_together = (('feed_index', 'trip_id'),)


class WheelchairAccessible(models.Model):
    wheelchair_accessible = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"wheelchair_accessible'


class WheelchairBoarding(models.Model):
    wheelchair_boarding = models.IntegerField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'gtfs\".\"wheelchair_boardings'
