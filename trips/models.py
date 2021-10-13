from __future__ import annotations

from django.db.models.query_utils import Q
from budget.models import DeviceDailyCarbonFootprint, EmissionBudgetLevel
from datetime import date, datetime, time, timedelta
from itertools import groupby
from typing import List, Optional
import calendar
import pandas as pd
import uuid
from django.db.models.aggregates import Sum
from django.db.models.functions import Trunc
from ranking import Ranking

import pytz
from django.utils import timezone
from django.db import transaction
from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django_prometheus.models import ExportModelOperationsMixin
from modeltrans.fields import TranslationField

from budget.enums import EmissionUnit, TimeResolution
from trips_ingest.models import DeviceHeartbeat, Location


LOCAL_TZ = pytz.timezone(settings.TIME_ZONE)


class InvalidStateError(Exception):
    pass


class Account(models.Model):
    key = models.CharField(max_length=50, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DeviceQuerySet(models.QuerySet):
    def by_name(self, name):
        return self.filter(friendly_name__iexact=name)

    def has_trips_during(self, start_date: date, end_date: date):
        start_time = LOCAL_TZ.localize(datetime.combine(start_date, time(0)))
        end_time = LOCAL_TZ.localize(datetime.combine(end_date + timedelta(days=1), time(0)))
        legs = Leg.objects.filter(start_time__gte=start_time, start_time__lt=end_time)
        return self.filter(trips__legs__in=legs).distinct()

    def enabled(self, enabled=True):
        return self.filter(enabled_at__isnull=not enabled)


class Device(ExportModelOperationsMixin('device'), models.Model):
    uuid = models.UUIDField(null=False, unique=True, db_index=True)
    token = models.CharField(max_length=50, null=True)
    platform = models.CharField(max_length=20, null=True)
    system_version = models.CharField(max_length=20, null=True)
    brand = models.CharField(max_length=20, null=True)
    model = models.CharField(max_length=40, null=True)

    friendly_name = models.CharField(max_length=40, null=True)
    debug_log_level = models.PositiveIntegerField(null=True)
    debugging_enabled_at = models.DateTimeField(null=True)
    custom_config = models.JSONField(null=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, blank=True, null=True, related_name='devices')

    enabled_at = models.DateTimeField(null=True)
    disabled_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(null=True)

    objects = DeviceQuerySet.as_manager()

    def generate_token(self):
        assert not self.token
        self.token = uuid.uuid4()

    def set_enabled(self, enabled: bool, time=None):
        with transaction.atomic():
            dev = Device.objects.select_for_update().filter(pk=self.pk).first()
            try:
                latest_event = dev.enable_events.latest()
                if latest_event.enabled == enabled:
                    raise InvalidStateError()
            except EnableEvent.DoesNotExist:
                pass

            if time is None:
                time = timezone.now()
            dev.enable_events.create(time=time, enabled=enabled)
            if enabled:
                dev.enabled_at = time
                dev.disabled_at = None
            else:
                dev.enabled_at = None
                dev.disabled_at = time
            dev.save(update_fields=['enabled_at', 'disabled_at'])

    @property
    def enabled(self):
        try:
            latest_event = self.enable_events.latest()
            return latest_event.enabled
        except EnableEvent.DoesNotExist:
            return False

    def update_daily_carbon_footprint(
        self, start_time: datetime, end_time: datetime, default_emissions: EmissionBudgetLevel = None
    ):
        if default_emissions is None:
            default_emissions = EmissionBudgetLevel.objects.get(identifier='bronze', year=start_time.year)
        start_date = LOCAL_TZ.localize(datetime.combine(start_time, time(0)))
        end_date = LOCAL_TZ.localize(datetime.combine(end_time, time(0)))
        summary = self.get_carbon_footprint_summary(
            start_date, end_date, time_resolution=TimeResolution.DAY,
            units=EmissionUnit.KG
        )
        date_summary = {fp['date']: fp for fp in summary}
        with transaction.atomic():
            self.daily_carbon_footprints.filter(date__gte=start_date, date__lte=end_date).delete()
            objs = []
            for cur_datetime in pd.date_range(start=start_date.date(), end=end_date.date()).to_pydatetime():
                cur_date = cur_datetime.date()
                cur_summary = date_summary.get(cur_date)
                carbon_footprint = cur_summary['carbon_footprint'] if cur_summary is not None else None
                default_footprint = default_emissions.calculate_for_date(cur_date, TimeResolution.DAY, EmissionUnit.KG)
                obj = self.create_device_daily_carbon_footprint(cur_date, carbon_footprint, default_footprint)
                objs.append(obj)
            DeviceDailyCarbonFootprint.objects.bulk_create(objs)

    def create_device_daily_carbon_footprint(self, date, carbon_footprint, default_footprint):
        average_footprint_used = False
        if carbon_footprint is None:
            if self.has_any_data_on_date(date):
                # Device has data, so has not moved
                carbon_footprint = 0
            else:
                # We don't know if the device has moved, so assume default footprint
                carbon_footprint = default_footprint
                average_footprint_used = True
        return DeviceDailyCarbonFootprint(
            device=self,
            date=date,
            carbon_footprint=carbon_footprint,
            average_footprint_used=average_footprint_used,
        )

    def get_ranking(self, month: date):
        start_date = month.replace(day=1)
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = start_date.replace(day=last_day)
        date_filter = Q(daily_carbon_footprints__date__gte=start_date, daily_carbon_footprints__date__lte=end_date)
        active_devs = Device.objects.enabled()
        devs = active_devs.annotate(
            carbon_sum=Sum('daily_carbon_footprints__carbon_footprint', filter=date_filter)
        ).filter(carbon_sum__isnull=False).order_by('carbon_sum')
        total = len(devs)
        for rank, dev in Ranking(devs, key=lambda x: x.carbon_sum, reverse=True):
            if dev == self:
                break
        else:
            rank = 0
        return dict(ranking=rank, maximum_rank=total)

    def daily_carbon_footprints_for_month(self, month: date):
        start_date = month.replace(day=1)
        last_day = calendar.monthrange(start_date.year, start_date.month)[1]
        end_date = start_date.replace(day=last_day)
        return self.daily_carbon_footprints.filter(date__gte=start_date, date__lte=end_date)

    def monthly_carbon_footprint(self, month: date):
        footprints = self.daily_carbon_footprints_for_month(month)
        return footprints.aggregate(Sum('carbon_footprint'))['carbon_footprint__sum']

    def num_active_days(self, month: date):
        """
        Return the number of days of the given month on which the average carbon footprint was *not* used for this
        device.
        """
        footprints = self.daily_carbon_footprints_for_month(month)
        return footprints.filter(average_footprint_used=False).count()

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
                start_date = start_date.replace(month=1, day=1)
        elif time_resolution == TimeResolution.MONTH:
            trunc_kind = 'month'
            if end_date is None:
                last_day = calendar.monthrange(start_date.year, start_date.month)[1]
                end_date = start_date.replace(day=last_day)
                start_date = start_date.replace(day=1)
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
            if time_resolution == TimeResolution.MONTH:
                rank_data = self.get_ranking(dt.date())
            else:
                rank_data = dict(ranking=0, maximum_rank=0)
            out.append(dict(
                date=dt.date(), per_mode=per_mode, length=total_length, carbon_footprint=total_footprint,
                **rank_data
            ))

        return out

    def has_any_data_on_date(self, date):
        return (DeviceHeartbeat.objects.filter(time__date=date, uuid=self.uuid).exists()
                or Location.objects.filter(time__date=date, uuid=self.uuid).exists())

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
        unique_together = (('mode', 'identifier'),)

    def __str__(self):
        return self.name


class DeviceDefaultModeVariant(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='default_mode_variants')
    mode = models.ForeignKey(TransportMode, on_delete=models.CASCADE, related_name='device_default_variants')
    variant = models.ForeignKey(TransportModeVariant, on_delete=models.CASCADE, related_name='device_defaults')

    class Meta:
        unique_together = (('device', 'mode'),)


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


class Trip(ExportModelOperationsMixin('trip'), models.Model):
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
        """Return the sum of carbon footprint of all legs in g"""
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
            end_time = self.get_start_time() + timedelta(hours=settings.ALLOWED_TRIP_UPDATE_HOURS)
        self._update_end_time = end_time
        return end_time

    def update_device_carbon_footprint(self):
        if self.first_leg is None or self.last_leg is None:
            return
        self.device.update_daily_carbon_footprint(
            start_time=self.first_leg.start_time,
            end_time=self.last_leg.end_time
        )

    def handle_leg_deletion(self, leg: Leg):
        active_legs = self.legs.active()
        if not active_legs:
            self.deleted_at = timezone.now()
            self.save(update_fields=['deleted_at'])

    def __str__(self):
        legs = list(self.legs.order_by('start_time'))
        if legs:
            length = 0
            for leg in legs:
                length += leg.length
            start_time = legs[0].start_time
            end_time = legs[-1].end_time
            duration = (end_time - start_time).total_seconds() / 60

            return 'Trip with %d legs, started %s (duration %.1f min), length %.1f km [%s]' % (
                len(legs), start_time, duration, length / 1000, self.device
            )
        return 'Trip with 0 legs [%s]' % self.device

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
    length = models.FloatField(help_text=_('Length in m'))
    carbon_footprint = models.FloatField(help_text=_('Carbon footprint in g CO2e'))
    nr_passengers = models.IntegerField(null=True)

    received_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True)

    objects = LegQuerySet.as_manager()

    class Meta:
        ordering = ('trip', 'start_time')

    def update_carbon_footprint(self):
        if self.mode_variant:
            emission_factor = self.mode_variant.emission_factor
        else:
            emission_factor = self.mode.emission_factor

        footprint = emission_factor * self.length / 1000
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

        start_time = self.start_time.astimezone(LOCAL_TZ)

        return '%sLeg [%s]: Started at %s (duration %.1f min), length %.1f km' % (
            deleted, mode_str, start_time, duration, self.length / 1000
        )


class UserLegUpdate(models.Model):
    leg = models.ForeignKey(Leg, on_delete=models.CASCADE, related_name='user_updates')
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()

    class Meta:
        ordering = ('leg', 'created_at')

    def __str__(self):
        return 'Update for %s (created at %s)' % (self.leg, self.created_at)


class LegLocationQuerySet(models.QuerySet):
    def _get_expired_query(self):
        now = timezone.now()
        expiry_time = now - timedelta(hours=settings.ALLOWED_TRIP_UPDATE_HOURS)
        qs = Q(leg__start_time__lte=expiry_time)
        return qs

    def expired(self):
        return self.filter(self._get_expired_query())

    def active(self):
        return self.exclude(self._get_expired_query())


class LegLocation(models.Model):
    leg = models.ForeignKey(Leg, on_delete=models.CASCADE, related_name='locations')
    loc = models.PointField(null=False, srid=4326)
    time = models.DateTimeField()
    speed = models.FloatField()

    objects = LegLocationQuerySet.as_manager()

    class Meta:
        ordering = ('leg', 'time')

    def __str__(self):
        time = self.time.astimezone(LOCAL_TZ)
        return '%s: %s (%.1f km/h)' % (time, self.loc, self.speed * 3.6)
