import uuid
from django.utils import timezone
from django.db import transaction
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class InvalidStateError(Exception):
    pass


class Device(models.Model):
    uuid = models.UUIDField(null=False, unique=True, db_index=True)
    token = models.CharField(max_length=50, null=True)
    platform = models.CharField(max_length=20, null=True)
    system_version = models.CharField(max_length=20, null=True)
    brand = models.CharField(max_length=20, null=True)
    model = models.CharField(max_length=20, null=True)

    def generate_token(self):
        assert not self.token
        self.token = uuid.uuid4()

    def set_enabled(self, enabled: bool):
        dev = Device.objects.select_for_update().filter(pk=self.pk).first()
        with transaction.atomic():
            try:
                latest_event = dev.enable_events.latest()
                if latest_event.enabled == enabled:
                    raise InvalidStateError()
            except EnableEvent.DoesNotExist:
                pass

            dev.enable_events.create(time=timezone.now(), enabled=enabled)

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
        return self.name


class EnableEvent(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='enable_events')
    time = models.DateTimeField()
    enabled = models.BooleanField()

    def __str__(self):
        return "%s [%s]: %s" % (self.device, self.time, self.enabled)

    class Meta:
        indexes = [models.Index(fields=['device', '-time'])]
        get_latest_by = 'time'


class Trip(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='trips')

    def get_start_time(self):
        return self.legs.all()[0].started_at

    def __str__(self):
        legs = list(self.legs.all())
        length = 0
        for leg in legs:
            length += leg.length

        started_at = legs[0].started_at
        ended_at = legs[-1].ended_at
        duration = (ended_at - started_at).total_seconds() / 60

        return 'Trip with %d legs, started %s (duration %.1f min), length %.1f km [%s]' % (
            len(legs), started_at, duration, length / 1000, self.device
        )

    class Meta:
        get_latest_by = 'legs__started_at'


class Leg(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='legs')
    deleted = models.BooleanField(default=False)
    mode = models.ForeignKey(TransportMode, on_delete=models.PROTECT)
    estimated_mode = models.ForeignKey(
        TransportMode, on_delete=models.PROTECT, related_name='+', db_index=False,
        null=True,
    )
    mode_confidence = models.FloatField(null=True)
    user_corrected_mode = models.ForeignKey(
        TransportMode, on_delete=models.PROTECT, related_name='+', db_index=False,
        null=True
    )

    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    start_loc = models.PointField(null=False, srid=4326)
    end_loc = models.PointField(null=False, srid=4326)
    length = models.FloatField()
    carbon_footprint = models.FloatField()
    nr_passengers = models.IntegerField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)

    class Meta:
        ordering = ('trip', 'start_time')

    def update_carbon_footprint(self):
        footprint = self.mode.emission_factor * self.length
        if self.mode.identifier == 'car' and self.nr_passengers:
            footprint /= (1 + self.nr_passengers)
        self.carbon_footprint = footprint

    def __str__(self):
        duration = (self.ended_at - self.started_at).total_seconds() / 60
        deleted = 'DELETED ' if self.deleted else False
        return '%sLeg [%s]: Started at %s (duration %.1s min), length %.1f km' % (
            deleted, self.mode.identifier, self.started_at, duration, self.length / 1000
        )


class UserLegUpdate(models.Model):
    leg = models.ForeignKey(Leg, on_delete=models.CASCADE, related_name='user_updates')
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()

    class Meta:
        ordering = ('leg', 'created_at')

    def __str__(self):
        return 'Update for %s (created at %s)' % (self.leg, self.created_at)


class LegLocation(models.Model):
    leg = models.ForeignKey(Leg, on_delete=models.CASCADE, related_name='locations')
    loc = models.PointField(null=False, srid=4326)
    time = models.DateTimeField()
    speed = models.FloatField()

    class Meta:
        ordering = ('leg', 'time')
