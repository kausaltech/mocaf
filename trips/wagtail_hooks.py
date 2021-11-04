from datetime import date, timedelta
import pandas as pd
from dateutil.relativedelta import relativedelta
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.core import hooks

from budget.models import DeviceDailyCarbonFootprint, Prize
from trips.models import Device, Leg


class StatisticsPanel:
    name = 'statistics'
    order = 200

    def __init__(self, request, heading, df):
        self.request = request
        self.heading = heading
        self.df = df

    def render(self):
        return render_to_string('trips/statistics.html', {
            'heading': self.heading,
            'table_html': self.df.to_html(index_names=False),
        }, request=self.request)


@hooks.register('construct_homepage_panels')
def add_statistics_panel(request, panels):
    # Calculate number of active devices per day in the last 14 days
    NR_DAYS = 14
    active_devices_per_day = []
    for nr_days in range(NR_DAYS + 1):
        day = date.today() - timedelta(days=NR_DAYS - nr_days)
        nr_devs = Device.objects.has_trips_during(day, day).count()
        active_devices_per_day.append(dict(day=day.isoformat(), value=nr_devs))

    if active_devices_per_day:
        df = pd.DataFrame.from_records(active_devices_per_day)
        df = df.set_index('day')
        df = df.rename(columns={'value': str(_("Number of devices"))})
        panels.append(StatisticsPanel(request, _("Active devices per day"), df))

    # Calculate number of active devices per month in the last year
    NR_MONTHS = 12
    active_devices_per_month = {}
    for i in range(NR_MONTHS + 1):
        start_date = date.today() - relativedelta(months=NR_MONTHS - i, day=1)
        end_date = date.today() - relativedelta(months=NR_MONTHS - i, day=31)
        nr_devs = Device.objects.has_trips_during(start_date, end_date).count()
        month_str = start_date.strftime('%Y-%m')
        active_devices_per_month[month_str] = nr_devs
    # We won't display a separate panel for active_devices_per_month, but use it to augment other panels

    # Calculate number of devices in each prize level
    one_year_ago = timezone.now() - relativedelta(years=1)
    prizes = (Prize.objects
              .filter(prize_month_start__gte=one_year_ago)
              .annotate(date=F('prize_month_start'), prize=F('budget_level__name'))
              .values('date', 'budget_level', 'prize')
              .annotate(count=Count('device'))
              .order_by('date', 'budget_level__carbon_footprint'))
    prizes = pd.DataFrame(data=prizes)
    if not prizes.empty:
        prizes['date'] = pd.to_datetime(prizes['date'])
        assert all(date.day == 1 for date in prizes['date'])
        # Print months in natural language
        prizes['date'] = prizes['date'].dt.strftime('%Y-%m')
        prizes = prizes.set_index('date')
        prizes = prizes.groupby(['date', 'prize'], sort=False)['count'].sum().unstack('prize')
        prizes[str(_('Total active devices'))] = [active_devices_per_month.get(month, 0) for month in prizes.index]
        panels.append(StatisticsPanel(request, _("Awarded prizes per month"), prizes))

    # Calculate histograms of carbon footprints for certain months
    monthly_footprints = (DeviceDailyCarbonFootprint.objects
                          .annotate(month=TruncMonth('date'))
                          .filter(month__gte=one_year_ago)
                          .values('device', 'month')
                          .annotate(monthly_footprint=Sum('carbon_footprint'))
                          .order_by())
    monthly_footprints = pd.DataFrame(data=monthly_footprints)
    bins = [i for i in range(0, 275, 25)] + [float('inf')]
    histograms = []
    months = list(sorted(monthly_footprints.month.unique()))
    for month in months:
        histogram = list(monthly_footprints[monthly_footprints.month == month]
                         .monthly_footprint
                         .value_counts(bins=bins))
        histograms.append(histogram)
    # Treat last bin separately because "250-inf kg" is ugly
    intervals = [f'{a}–{b} kg' for a, b in zip(bins[:-1], bins[1:-1])] + [f'≥ {bins[-2]} kg']
    histograms_df = pd.DataFrame(data=histograms, index=months, columns=intervals)
    if not histograms_df.empty:
        histograms_df = histograms_df.reset_index()
        histograms_df['index'] = pd.to_datetime(histograms_df['index'])
        histograms_df['index'] = histograms_df['index'].dt.strftime('%Y-%m')
        histograms_df = histograms_df.set_index('index')
        histograms_df[str(_('Total active devices'))] = [active_devices_per_month.get(month, 0)
                                                         for month in histograms_df.index]
        panels.append(StatisticsPanel(request, _("Number of devices by carbon footprint"), histograms_df))
