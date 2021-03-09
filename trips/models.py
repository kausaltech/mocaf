from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class Device(models.Model):
    uuid = models.UUIDField(null=False, unique=True, db_index=True)
    token = models.CharField(max_length=50)

    def __str__(self):
        return str(self.uuid)


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
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(db_index=True)
    start_loc = models.PointField(null=False, srid=4326)
    end_loc = models.PointField(null=False, srid=4326)
    length = models.FloatField()
    carbon_footprint = models.FloatField()

    class Meta:
        ordering = ('trip', 'started_at')


class LegLocation(models.Model):
    leg = models.ForeignKey(Leg, on_delete=models.CASCADE, related_name='locations')
    loc = models.PointField(null=False, srid=4326)
    time = models.DateTimeField()
    speed = models.FloatField()

    class Meta:
        ordering = ('leg', 'time')
