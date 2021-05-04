from __future__ import annotations
from datetime import date, datetime, time, timedelta
from itertools import groupby
from typing import List, Optional
import calendar
import uuid
from django.db.models.aggregates import Sum
from django.db.models.functions import Trunc

import pytz
from django.utils import timezone
from django.db import transaction
from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from modeltrans.fields import TranslationField

from budget.enums import EmissionUnit, TimeResolution


LOCAL_TZ = pytz.timezone(settings.TIME_ZONE)


class InvalidStateError(Exception):
    pass


class Device(models.Model):
    uuid = models.UUIDField(null=False, unique=True, db_index=True)
    token = models.CharField(max_length=50, null=True)
    platform = models.CharField(max_length=20, null=True)
    system_version = models.CharField(max_length=20, null=True)
    brand = models.CharField(max_length=20, null=True)
    model = models.CharField(max_length=20, null=True)
    created_at = models.DateTimeField(null=True)

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

    def update_carbon_footprint(self, start_time: datetime, end_time: datetime):
        # from budget.models import DeviceDailyCarbonFootprint
        # DeviceDailyCarbonFootprint.update_for_period(self.device, start_time, end_time)
        pass

    def _get_transport_modes(self):
        modes = getattr(self, '_mode_cache', None)
        if not modes:
            self._mode_cache = {mode.id: mode for mode in TransportMode.objects.all()}
        return self._mode_cache

    def get_carbon_footprint_summary(
        self, start_date: date, end_date: date = None,
        time_resolution: TimeResolution = TimeResolution.DAY,
        units: EmissionUnit = EmissionUnit.G
    ):
        if end_date is not None:
            assert end_date >= start_date

        modes = self._get_transport_modes()

        if time_resolution == TimeResolution.YEAR:
            trunc_kind = 'year'
            if end_date is None:
                end_date = start_date.replace(month=12, day=31)
        elif time_resolution == TimeResolution.MONTH:
            trunc_kind = 'month'
            if end_date is None:
                last_day = calendar.monthrange(start_date.year, start_date.month)[1]
                end_date = start_date.replace(day=last_day)
        elif time_resolution == TimeResolution.DAY:
            trunc_kind = 'day'
            if end_date is None:
                end_date = start_date
        else:
            raise Exception('Invalid time resolution')

        start_time = LOCAL_TZ.localize(datetime.combine(start_date, time(0)))
        end_time = LOCAL_TZ.localize(datetime.combine(end_date + timedelta(days=1), time(0)))

        annotation = {'date': Trunc('start_time', trunc_kind, tzinfo=LOCAL_TZ)}

        legs = Leg.objects.active().filter(trip__device=self)\
            .filter(start_time__gte=start_time, start_time__lt=end_time)\
            .annotate(**annotation)\
            .values('date', 'mode').annotate(
                carbon_footprint=Sum('carbon_footprint'),
                length=Sum('length')
            ).order_by('date')

        out = []
        in_kg = units == EmissionUnit.KG
        for dt, data in groupby(legs, lambda x: x['date']):
            per_mode = [dict(
                mode=modes[x['mode']],
                carbon_footprint=x['carbon_footprint'] if not in_kg else x['carbon_footprint'] / 1000,
                length=x['length']
            ) for x in data]
            total_length = sum([x['length'] for x in per_mode])
            total_footprint = sum([x['carbon_footprint'] for x in per_mode])
            out.append(dict(
                date=dt.date(), per_mode=per_mode, length=total_length, carbon_footprint=total_footprint,
            ))

        return out

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

    i18n = TranslationField(fields=('name',))

    class Meta:
        verbose_name = _('Transport mode')
        verbose_name_plural = _('Transport modes')

    def __str__(self):
        return self.name


class TransportModeVariant(models.Model):
    mode = models.ForeignKey(TransportMode, on_delete=models.CASCADE, related_name='variants')
    identifier = models.CharField(
        max_length=20, unique=True, verbose_name=_('Identifier'),
        editable=False,
    )
    name = models.CharField(max_length=50, verbose_name=_('Name'))
    emission_factor = models.FloatField(
        null=True, verbose_name=_('Emission factor'),
        help_text=_('Emission factor of transport mode in g (CO2e)/passenger-km')
    )

    i18n = TranslationField(fields=('name',))

    class Meta:
        verbose_name = _('Transport mode variant')
        verbose_name_plural = _('Transport mode variants')

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


class TripQuerySet(models.QuerySet):
    def annotate_times(self):
        if getattr(self, '_times_annotated', False):
            return self

        qs = self.annotate(
            start_time=models.Min('legs__start_time'),
            end_time=models.Max('legs__end_time'),
        )
        qs._times_annotated = True
        return qs

    def started_during(self, start_time, end_time):
        qs = self.annotate_times()
        qs = qs.filter(start_time__gte=start_time)\
            .filter(start_time__lt=end_time)
        return qs

    def active(self):
        return self.filter(deleted_at__isnull=True)


class Trip(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='trips')
    deleted_at = models.DateTimeField(null=True)

    objects = TripQuerySet.as_manager()

    _ordered_legs: List[Leg]

    def _ensure_ordered_legs(self):
        if hasattr(self, '_ordered_legs'):
            return
        self._ordered_legs = list(self.legs.active().order_by('start_time'))

    @property
    def first_leg(self) -> Optional[Leg]:
        self._ensure_ordered_legs()
        if not self._ordered_legs:
            return None
        return self._ordered_legs[0]

    @property
    def last_leg(self) -> Optional[Leg]:
        self._ensure_ordered_legs()
        if not self._ordered_legs:
            return None
        return self._ordered_legs[-1]

    @property
    def length(self) -> float:
        self._ensure_ordered_legs()
        length = 0
        for leg in self._ordered_legs:
            length += leg.length
        return length

    @property
    def carbon_footprint(self) -> float:
        self._ensure_ordered_legs()
        footprint = 0
        for leg in self._ordered_legs:
            footprint += leg.carbon_footprint
        return footprint

    def get_start_time(self):
        return self.legs.order_by('start_time')[0].start_time

    def get_update_end_time(self):
        end_time = getattr(self, '_update_end_time', None)
        if not end_time:
            # Hard-code to two weeks for now
            end_time = self.get_start_time() + timedelta(days=14)
        self._update_end_time = end_time
        return end_time

    def update_carbon_footprint(self):
        all_legs = list(self.legs.order_by('start_time'))
        self.device.update_carbon_footprint(
            start_time=all_legs[0].start_time,
            end_time=all_legs[-1].end_time
        )

    def handle_leg_deletion(self, leg: Leg):
        active_legs = self.legs.active()
        if not active_legs:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])

    def __str__(self):
        legs = list(self.legs.all())
        length = 0
        for leg in legs:
            length += leg.length

        start_time = legs[0].start_time
        end_time = legs[-1].end_time
        duration = (end_time - start_time).total_seconds() / 60

        return 'Trip with %d legs, started %s (duration %.1f min), length %.1f km [%s]' % (
            len(legs), start_time, duration, length / 1000, self.device
        )

    class Meta:
        get_latest_by = 'legs__start_time'


class LegQuerySet(models.QuerySet):
    def active(self):
        return self.filter(deleted_at__isnull=True)


class Leg(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='legs')
    deleted_at = models.DateTimeField(null=True)
    mode = models.ForeignKey(
        TransportMode, on_delete=models.PROTECT, related_name='legs'
    )
    mode_variant = models.ForeignKey(
        TransportModeVariant, on_delete=models.SET_NULL, null=True, blank=True, related_name='legs',
    )

    estimated_mode = models.ForeignKey(
        TransportMode, on_delete=models.PROTECT, related_name='+', db_index=False,
        null=True,
    )
    mode_confidence = models.FloatField(null=True)
    user_corrected_mode = models.ForeignKey(
        TransportMode, on_delete=models.PROTECT, related_name='+', db_index=False,
        null=True
    )
    user_corrected_mode_variant = models.ForeignKey(
        TransportModeVariant, on_delete=models.SET_NULL, related_name='+', db_index=False,
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

    objects = LegQuerySet.as_manager()

    class Meta:
        ordering = ('trip', 'start_time')

    def update_carbon_footprint(self):
        footprint = self.mode.emission_factor * self.length / 1000
        if self.mode.identifier == 'car' and self.nr_passengers:
            footprint /= (1 + self.nr_passengers)
        self.carbon_footprint = footprint

    def can_user_update(self) -> bool:
        return timezone.now() < self.trip.get_update_end_time()

    def __str__(self):
        duration = (self.end_time - self.start_time).total_seconds() / 60
        deleted = 'DELETED ' if self.deleted_at else ''
        mode_str = self.mode.identifier
        if self.mode_variant:
            mode_str += ' (%s)' % self.mode_variant.identifier

        return '%sLeg [%s]: Started at %s (duration %.1s min), length %.1f km' % (
            deleted, mode_str, self.start_time, duration, self.length / 1000
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
