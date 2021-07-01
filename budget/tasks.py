import datetime
import logging
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from budget.enums import TimeResolution, EmissionUnit
from budget.models import EmissionBudgetLevel, Prize
from budget.prize_api import PrizeApi
from trips.models import Device

logger = logging.getLogger(__name__)


class MonthlyPrizeTask:
    budget_level_identifier = None

    # Next lower budget level; if footprint is smaller, do not award the budget_level_identifier prize (but hopefully
    # the better one)
    next_budget_level_identifier = None

    def __init__(
            self, budget_level_identifier, next_budget_level_identifier=None, now=None, dry_run=False, prize_api=None,
            default_emissions=None
    ):
        """
        `budget_level_identifier` is the budget level for which to award a prize if footprint is smaller.
        `next_budget_level_identifier` is the next lower budget level; if footprint is smaller, do not award the
        `budget_level_identifier` prize (but you should make sure to award the better one by creating a new
        `MonthlyPrizeTask` with that level as `budget_level_identifier`).
        """
        if now is None:
            now = timezone.now()
        if prize_api is None:
            prize_api = PrizeApi()

        self.now = now
        self.dry_run = dry_run
        self.prize_api = prize_api

        one_month_ago = self.now - relativedelta(months=1)
        start_date = one_month_ago.date().replace(day=1)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_date = self.now.date().replace(day=1) - datetime.timedelta(days=1)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        self.prize_month_start = start_date

        # Update carbon footprints of all (enabled) devices to make sure there are no gaps on days without data
        devices = Device.objects.filter(enabled_at__isnull=False)
        for device in devices:
            # We shouldn't call this if dry_run is True, but it probably doesn't break things if we do
            device.update_daily_carbon_footprint(start_datetime, end_datetime, default_emissions)
        self.footprints = {device: device.monthly_carbon_footprint(start_date) for device in devices}

        self.budget_level = EmissionBudgetLevel.objects.get(
            identifier=budget_level_identifier,
            year=self.prize_month_start.year
        )
        self.prize_threshold = self.budget_level.calculate_for_date(
            self.prize_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )
        if next_budget_level_identifier is None:
            self.next_prize_threshold = None
        else:
            next_budget_level = EmissionBudgetLevel.objects.get(
                identifier=next_budget_level_identifier,
                year=self.prize_month_start.year
            )
            self.next_prize_threshold = next_budget_level.calculate_for_date(
                self.prize_month_start, TimeResolution.MONTH, EmissionUnit.KG
            )

    def award_prizes(self, devices=None):
        """
        Award the prize to the given devices.

        If `devices` is None, the recipients will the result of calling `recipients()`.
        """
        if devices is None:
            devices = self.recipients()

        logger.info("Awarding prizes")
        logger.debug(f"Awarding prizes to {len(devices)} devices")
        for device in devices:
            self.award_prize(device)

    def recipients(self):
        """Return devices that should receive a prize for the calendar month preceding the one of `self.now`."""
        # Don't send anything to devices that already got a prize for that month
        excluded_devices = (Prize.objects
                            .filter(prize_month_start=self.prize_month_start)
                            .values('device'))

        eligible_devices = [dev.id for dev, footprint in self.footprints.items() if self.footprint_eligible(footprint)]

        return (Device.objects
                .filter(enabled_at__isnull=False)
                .filter(id__in=eligible_devices)
                .exclude(id__in=excluded_devices))

    def footprint_eligible(self, footprint):
        """Return true iff devices with the given footprint are eligible for getting the prize."""
        eligible = footprint <= self.prize_threshold
        if self.next_prize_threshold is not None:
            eligible = eligible and footprint > self.next_prize_threshold
        return eligible

    @transaction.atomic
    def award_prize(self, device):
        if self.dry_run:
            print(f"Awarding prize {self.budget_level} to device {device.uuid} for month {self.prize_month_start}")
        else:
            prize = Prize.objects.create(
                device=device,
                budget_level=self.budget_level,
                prize_month_start=self.prize_month_start
            )
            # TODO: Award all prizes in a single API call
            self.prize_api.award([prize])


@shared_task
def award_prizes(budget_level_identifier, next_budget_level_identifier=None, devices=None, **kwargs):
    task = MonthlyPrizeTask(budget_level_identifier, next_budget_level_identifier, **kwargs)
    task.award_prizes(devices)
