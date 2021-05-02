import calendar
from enum import Enum, auto
from datetime import date, datetime, time, timedelta
from django.db.models.aggregates import Min
from modeltrans.fields import TranslationField
import pytz
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from trips.models import Device


LOCAL_TZ = pytz.timezone(settings.TIME_ZONE)


class EmissionUnit(Enum):
    G = auto()
    KG = auto()


class TimeResolution(Enum):
    DAY = auto()
    WEEK = auto()
    MONTH = auto()
    YEAR = auto()


class EmissionBudgetLevel(models.Model):
    identifier = models.CharField(max_length=50)
    name = models.CharField(max_length=50)
    carbon_footprint = models.FloatField(
        verbose_name=_('Maximum emission amount'),
        help_text=_('Amount of carbon emissions per resident per year (in kgs of CO2e.) to reach this level'),
    )
    year = models.PositiveIntegerField(
        verbose_name=_('Year'),
        help_text=_('Year to which this level applies')
    )

    i18n = TranslationField(fields=('name',))

    class Meta:
        verbose_name = _('Emission budget level')
        verbose_name_plural = _('Emission budget levels')
        unique_together = (('identifier', 'year'),)
        ordering = ('year', 'carbon_footprint',)

    def calculate_for_date(
        self, date: date, time_resolution: TimeResolution,
        units: EmissionUnit = EmissionUnit.KG
    ) -> float:
        assert date.year == self.year
        amount = self.carbon_footprint
        days_in_year = 365 if not calendar.isleap(date.year) else 366
        if time_resolution == TimeResolution.YEAR:
            pass
        elif time_resolution == TimeResolution.MONTH:
            days_in_month = calendar.monthrange(date.year, date.month)[1]
            amount = amount / days_in_year * days_in_month
        elif time_resolution == TimeResolution.WEEK:
            amount = amount / days_in_year * 7
        elif time_resolution == TimeResolution.DAY:
            amount = amount / days_in_year
        else:
            raise Exception('Invalid time resolution')
        if units == EmissionUnit.G:
            amount *= 1000
        return amount

    def __str__(self):
        return '%s [%d]' % (self.name, self.year)


class DeviceDailyCarbonFootprint(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name='daily_carbon_footprints'
    )
    date = models.DateField()
    carbon_footprint = models.FloatField()

    @classmethod
    def update_for_date(cls, device, date: date):
        all_trips = device.trips.annotate(start_time=Min('legs__start_time'))
        start_time = LOCAL_TZ.localize(datetime.combine(date, time(0)))
        trips_for_date = all_trips.filter(start_time__gte=start_time)\
            .filter(start_time__lt=start_time + timedelta(hours=24))
        for trip in trips_for_date:
            print(trip)

    @classmethod
    def update_for_period(cls, device, start_time: datetime, end_time: datetime):
        pass

    class Meta:
        ordering = (('device', 'date'),)
        unique_together = (('device', 'date'),)
