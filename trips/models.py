from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class LocationImport(models.Model):
    id = models.IntegerField(primary_key=True)
    time = models.IntegerField(null=False)
    uid = models.CharField(max_length=50)
    lat = models.FloatField(null=True)
    lon = models.FloatField(null=True)
    acc = models.IntegerField(null=True)
    atype = models.CharField(max_length=30, null=True)
    aconf = models.IntegerField(null=True)
    speed = models.FloatField(null=True)
    heading = models.FloatField(null=True)
    ms = models.IntegerField(null=True)


class SensorSampleImport(models.Model):
    id = models.IntegerField(primary_key=True)
    uid = models.CharField(max_length=50)
    time = models.IntegerField(null=False)
    ms = models.IntegerField(null=True)
    x = models.FloatField(null=False)
    y = models.FloatField(null=False)
    z = models.FloatField(null=False)
    type = models.CharField(null=False, max_length=20)


class ActivityTypeChoices(models.TextChoices):
    UNKNOWN = 'unknown', _('Unknown')
    STILL = 'still', _('Still')
    ON_FOOT = 'on_foot', _('On foot')
    WALKING = 'walking', _('Walking')
    RUNNING = 'running', _('Running')
    ON_BICYCLE = 'on_bicycle', _('On bicycle')
    IN_VEHICLE = 'in_vehicle', _('In vehicle')


class Location(models.Model):
    time = models.DateTimeField(null=False)
    uuid = models.UUIDField(null=False)
    loc = models.PointField(null=False, srid=4326)
    loc_error = models.FloatField(null=True)
    atype = models.CharField(choices=ActivityTypeChoices.choices, null=True, max_length=20)
    aconf = models.FloatField(null=True)
    speed = models.FloatField(null=True)
    heading = models.FloatField(null=True)
    sensor_data_count = models.PositiveIntegerField(null=True)

    public_fields = ['time', 'uuid', 'loc', 'acc', 'atype', 'aconf', 'speed', 'heading']

    def __str__(self):
        return '%s [%s]' % (self.uuid, self.time)

    class Meta:
        unique_together = (('uuid', 'time'),)
        indexes = [
            models.Index(fields=['uuid', '-time']),
        ]


class SensorTypeChoices(models.TextChoices):
    UNKNOWN = 'acce', _('Accelerometer')
    STILL = 'gyro', _('Gyroscope')


class SensorSample(models.Model):
    time = models.DateTimeField(null=False)
    uuid = models.UUIDField(null=False)
    x = models.FloatField(null=False)
    y = models.FloatField(null=False)
    z = models.FloatField(null=False)
    type = models.CharField(null=False, max_length=20, choices=SensorTypeChoices.choices)

    class Meta:
        unique_together = (('uuid', 'time'),)
        indexes = [
            models.Index(fields=['uuid', '-time']),
        ]


class Device(models.Model):
    uuid = models.UUIDField(null=False, unique=True)
    token = models.CharField(max_length=50)


class TransportMode(models.Model):
    identifier = models.CharField(
        max_length=20, unique=True, verbose_name=_('Identifier'),
        editable=False,
    )
    name = models.CharField(max_length=50, verbose_name=_('Name'))
    emission_factor = models.FloatField(
        null=True, verbose_name=_('Emission factor'),
        help_text=_('Emission factor of transport mode in g (CO2e)/passenger-km')
    )

    class Meta:
        verbose_name = _('Transport mode')
        verbose_name_plural = _('Transport modes')

    def __str__(self):
        return self.label


class Trip(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='trips')


class Leg(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='legs')
    mode = models.ForeignKey(TransportMode, on_delete=models.PROTECT)
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    length = models.FloatField()
    carbon_footprint = models.FloatField()


class LegLocation(models.Model):
    leg = models.ForeignKey(Leg, on_delete=models.CASCADE, related_name='locations')
    loc = models.PointField(null=False, srid=4326)
    time = models.DateTimeField()
    speed = models.FloatField()

    class Meta:
        ordering = ('leg', 'time')
