from __future__ import annotations

from datetime import date
from typing import Type
from django.db import transaction, IntegrityError
from django.db.models import F
from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.postgres.fields import ArrayField

from trips.models import LOCAL_TZ, Trip, TransportMode, Device
from modeltrans.fields import TranslationField


gps_srs = SpatialReference(4326)
local_srs = SpatialReference(settings.LOCAL_SRS)
gps_to_local = CoordTransform(gps_srs, local_srs)


class AreaType(models.Model):
    identifier = models.CharField(
        max_length=20, unique=True, verbose_name=_('Identifier'),
        editable=False,
    )
    name = models.CharField(max_length=50, verbose_name=_('Name'))

    wfs_url = models.URLField(null=True)
    wfs_type_name = models.CharField(max_length=200, null=True)
    is_poi = models.BooleanField(default=False)

    # Topologies of all of the areas in TopoJSON (EPSG:4326)
    topojson = models.TextField(null=True)

    # Topologies of all of the areas in GeoJSON (EPSG:4326)
    geojson = models.TextField(null=True)

    # Cache data summaries here for quicker access
    daily_trips_date_range = ArrayField(models.DateField(null=True), blank=True, null=True)
    daily_lengths_date_range = ArrayField(models.DateField(null=True), blank=True, null=True)
    daily_poi_trips_date_range = ArrayField(models.DateField(null=True), blank=True, null=True)

    i18n = TranslationField(fields=('name',))

    def update_summaries(self):
        ret = DailyModeSummary.objects.filter(area__type=self).aggregate(
            min_date=models.Min('date'),
            max_date=models.Max('date')
        )
        self.daily_lengths_date_range = [ret['min_date'], ret['max_date']]

        ret = DailyTripSummary.objects.filter(
            models.Q(origin__type=self) | models.Q(dest__type=self)
        ).aggregate(
            min_date=models.Min('date'),
            max_date=models.Max('date')
        )
        self.daily_trips_date_range = [ret['min_date'], ret['max_date']]

        ret = DailyPoiTripSummary.objects.filter(models.Q(poi__type=self)).aggregate(
            min_date=models.Min('date'),
            max_date=models.Max('date')
        )
        self.daily_poi_trips_date_range = [ret['min_date'], ret['max_date']]

        self.save(update_fields=[
            'daily_lengths_date_range', 'daily_trips_date_range', 'daily_poi_trips_date_range'
        ])

    def __str__(self):
        return self.name


class AreaProperty(models.Model):
    area_type = models.ForeignKey(AreaType, on_delete=models.CASCADE, related_name='properties_meta')
    identifier = models.CharField(max_length=100)
    order = models.PositiveIntegerField()
    description = models.CharField(max_length=200)

    class Meta:
        unique_together = (('area_type', 'identifier'),)
        ordering = ('area_type', 'order')

    def __str__(self):
        return self.description


class Area(models.Model):
    type = models.ForeignKey(AreaType, on_delete=models.CASCADE, related_name='areas')
    identifier = models.CharField(
        max_length=20, verbose_name=_('Identifier'), editable=False,
    )
    name = models.CharField(max_length=50, verbose_name=_('Name'))
    geometry = models.MultiPolygonField(null=False, srid=settings.LOCAL_SRS, db_index=True)
    geometry_masked = models.MultiPolygonField(null=True, srid=settings.LOCAL_SRS, db_index=True)
    centroid = models.PointField(null=True, srid=settings.LOCAL_SRS, db_index=True)

    i18n = TranslationField(fields=('name',))

    class Meta:
        unique_together = (('type', 'identifier'),)

    def __str__(self):
        return '%s: %s (%s)' % (str(self.type), self.name, self.identifier)


class AreaPropertyValue(models.Model):
    area = models.ForeignKey(Area, related_name='property_values', on_delete=models.CASCADE)
    property = models.ForeignKey(AreaProperty, related_name='area_values', on_delete=models.CASCADE)
    value = models.FloatField()

    class Meta:
        unique_together = (('area', 'property'),)

    def __str__(self):
        return '%s: %s' % (self.area, self.property)


class TripSummary(models.Model):
    class OtherPrimaryMode(models.IntegerChoices):
        MULTIMODAL = 1, _('Multi-modal with no primary transport mode')
        MULTIMODAL_PUBLIC = 2, _('Multi-modal with public transport')

    trip = models.OneToOneField('trips.Trip', related_name='summary', on_delete=models.CASCADE)
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField()

    primary_mode = models.ForeignKey('trips.TransportMode', null=True, on_delete=models.CASCADE)
    primary_mode_other = models.IntegerField(choices=OtherPrimaryMode.choices, null=True)
    length = models.FloatField()
    carbon_footprint = models.FloatField()

    start_loc = models.PointField(srid=settings.LOCAL_SRS)
    end_loc = models.PointField(srid=settings.LOCAL_SRS)

    created_at = models.DateTimeField(auto_now=True)

    @classmethod
    def from_trip(kls, trip: Trip, modes: list[TransportMode]):
        PRIMARY_THRESHOLD = 0.8

        first_leg = trip.first_leg
        last_leg = trip.last_leg
        obj = kls(trip=trip)
        obj.start_time = first_leg.start_time
        obj.end_time = last_leg.end_time

        per_mode = {}
        total = 0
        cfp = 0
        for leg in trip._ordered_legs:
            if leg.mode_id not in per_mode:
                per_mode[leg.mode_id] = 0
            per_mode[leg.mode_id] += leg.length
            total += leg.length
            cfp += leg.carbon_footprint

        for mode_id, mode_length in per_mode.items():
            if mode_length > PRIMARY_THRESHOLD * total:
                primary_mode = mode_id
                break
        else:
            primary_mode = None

        obj.primary_mode_id = primary_mode
        obj.length = total
        obj.carbon_footprint = cfp
        obj.start_loc = trip.first_leg.start_loc
        obj.end_loc = trip.last_leg.end_loc
        return obj

    def __str__(self):
        return 'Stats for %s' % str(self.trip)


class DailyModeSummary(models.Model):
    date = models.DateField(db_index=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE)
    mode = models.ForeignKey('trips.TransportMode', on_delete=models.CASCADE)
    length = models.FloatField()
    trips = models.IntegerField(null=True)

    class Meta:
        unique_together = (('date', 'area', 'mode'),)


class DailyTripSummary(models.Model):
    date = models.DateField(db_index=True)
    origin = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='+', null=True)
    dest = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='+', null=True)
    mode = models.ForeignKey('trips.TransportMode', on_delete=models.CASCADE, null=True)
    mode_specifier = models.CharField(max_length=20, null=True)

    trips = models.IntegerField()
    length = models.FloatField(null=True)

    class Meta:
        unique_together = (('date', 'origin', 'dest', 'mode', 'mode_specifier'),)


class DailyPoiTripSummary(models.Model):
    date = models.DateField(db_index=True)
    poi = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='trip_summaries')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='+', null=True)
    is_inbound = models.BooleanField()
    mode = models.ForeignKey('trips.TransportMode', on_delete=models.CASCADE, null=True)
    mode_specifier = models.CharField(max_length=20, null=True)

    trips = models.IntegerField()
    length = models.FloatField(null=True)

    class Meta:
        unique_together = (('date', 'poi', 'area', 'is_inbound', 'mode', 'mode_specifier'),)


class DeviceDailyAPIActivity(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name='daily_api_activity'
    )
    date = models.DateField()
    nr_queries = models.PositiveIntegerField(default=1)

    @classmethod
    def record_api_hit(cls: Type[DeviceDailyAPIActivity], device: Device):
        today = date.today()
        with transaction.atomic():
            kwargs = dict(device=device, date=today)
            obj = cls.objects.filter(**kwargs).select_related('device').select_for_update().first()
            if obj is None:
                try:
                    DeviceDailyAPIActivity.objects.create(**kwargs)
                except IntegrityError:
                    pass
            else:
                obj.nr_queries = obj.nr_queries + 1
                obj.save()

    class Meta:
        unique_together = (('device', 'date'),)
