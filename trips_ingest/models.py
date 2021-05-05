from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class ReceiveData(models.Model):
    data = models.JSONField()
    received_at = models.DateTimeField(db_index=True)
    imported_at = models.DateTimeField(null=True, db_index=True)
    import_failed = models.BooleanField(null=True)

    class Meta:
        ordering = ('received_at',)


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
    created_at = models.IntegerField(null=True)
    debug = models.IntegerField(null=True)


class DeviceImport(models.Model):
    id = models.IntegerField(primary_key=True)
    uid = models.CharField(max_length=50)
    platform = models.CharField(max_length=20, null=True)
    system_version = models.CharField(max_length=20, null=True)
    brand = models.CharField(max_length=20, null=True)
    model = models.CharField(max_length=20, null=True)
    created_at = models.IntegerField(null=True)


class HeartbeatImport(models.Model):
    id = models.IntegerField(primary_key=True)
    time = models.IntegerField(null=False)
    ms = models.IntegerField(null=True)
    uid = models.CharField(max_length=50)
    debug = models.IntegerField(null=True)


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
    time = models.DateTimeField(primary_key=True)
    uuid = models.UUIDField()
    loc = models.PointField(null=False, srid=settings.LOCAL_SRS)
    loc_error = models.FloatField(null=True)
    atype = models.CharField(choices=ActivityTypeChoices.choices, null=True, max_length=20)
    aconf = models.FloatField(null=True)
    speed = models.FloatField(null=True)
    speed_error = models.FloatField(null=True)
    altitude = models.FloatField(null=True)
    altitude_error = models.FloatField(null=True)
    heading = models.FloatField(null=True)
    heading_error = models.FloatField(null=True)
    odometer = models.FloatField(null=True)
    is_moving = models.BooleanField(null=True)
    battery_charging = models.BooleanField(null=True)
    created_at = models.DateTimeField(null=True)
    debug = models.BooleanField(default=False)
    sensor_data_count = models.PositiveIntegerField(null=True)

    public_fields = ['time', 'uuid', 'loc', 'acc', 'atype', 'aconf', 'speed', 'heading']

    class Meta:
        managed = False
        db_table = 'trips_ingest_location'

    def __str__(self):
        return '%s [%s]' % (self.uuid, self.time)


class DeviceHeartbeat(models.Model):
    time = models.DateTimeField()
    uuid = models.UUIDField()
    created_at = models.DateTimeField(null=True)

    class Meta:
        unique_together = ('uuid', 'time')


class SensorTypeChoices(models.TextChoices):
    ACCELEROMETER = 'acce', _('Accelerometer')
    GYROSCOPE = 'gyro', _('Gyroscope')


class SensorSample(models.Model):
    time = models.DateTimeField(null=False, primary_key=True)
    uuid = models.UUIDField(null=False)
    x = models.FloatField(null=False)
    y = models.FloatField(null=False)
    z = models.FloatField(null=False)
    type = models.CharField(null=False, max_length=20, choices=SensorTypeChoices.choices)

    class Meta:
        managed = False
        db_table = 'trips_ingest_sensorsample'
