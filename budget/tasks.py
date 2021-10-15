import datetime
import logging
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from budget.enums import TimeResolution, EmissionUnit
from budget.models import EmissionBudgetLevel, Prize
from budget.prize_api import PrizeApi
from trips.models import Account

logger = logging.getLogger(__name__)


class MonthlyPrizeTask:
    def __init__(
        self, budget_level_identifier, next_budget_level_identifier=None, now=None, dry_run=False, accounts=None,
        force=False, prize_api=None, default_emissions=None, min_active_days=0
    ):
        """
        Award prizes for the month preceding `now` and the given budget level.

        `budget_level_identifier` is the budget level for which to award a prize if footprint is smaller.
        `next_budget_level_identifier` is the next lower budget level; if footprint is smaller, do not award the
        `budget_level_identifier` prize (but you should make sure to award the better one by creating a new
        `MonthlyPrizeTask` with that level as `budget_level_identifier`).
        `accounts` can be set to a QuerySet smaller than Account.objects.all() to limit the potential recipients.
        If `force` is True, attempt to award the prize to all accounts in `accounts` (or all if `accounts` is not set)
        regardless of whether they qualify for the prize.
        `min_active_days` is the number of days of the relevant month that the account must have been active in order to
        receive a prize.
        """
        if now is None:
            now = timezone.now()
        if prize_api is None:
            prize_api = PrizeApi()

        self.now = now
        self.dry_run = dry_run
        self.force = force
        self.prize_api = prize_api
        self.min_active_days = min_active_days

        one_month_ago = self.now - relativedelta(months=1)
        start_date = one_month_ago.date().replace(day=1)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_date = self.now.date().replace(day=1) - datetime.timedelta(days=1)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        self.prize_month_start = start_date

        if accounts is None:
            accounts = Account.objects.all()

        # Ensure the processed accounts have at least one detected trip during the
        # time period.
        accounts = accounts.has_trips_during(start_date, end_date)
        self.accounts = accounts

        # Update carbon footprints of all relevant accounts to make sure there are no gaps on days without data
        for account in accounts:
            # We shouldn't call this if dry_run is True, but it probably doesn't break things if we do
            account.update_daily_carbon_footprint(start_datetime, end_datetime, default_emissions)
        self.footprints = {account: account.monthly_carbon_footprint(start_date) for account in accounts}
        self.num_active_days = {account: account.num_active_days(start_date) for account in accounts}

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

    def award_prizes(self):
        if self.force:
            recipients = self.accounts
        else:
            recipients = self.recipients()
        logger.info("Awarding prizes")
        logger.debug(f"Awarding prizes to {len(recipients)} accounts")
        for account in recipients:
            self.award_prize(account)

    def recipients(self):
        """Return accounts that should receive a prize for the calendar month preceding the one of `self.now`."""
        # Don't send anything to accounts that already got a prize for that month
        earlier_recipients = (Prize.objects
                              .filter(prize_month_start=self.prize_month_start)
                              .values('account'))

        eligible_footprint_accounts = [
            account.id for account, footprint in self.footprints.items() if self.footprint_eligible(footprint)
        ]

        sufficiently_active_accounts = [
            acc.id for acc, num_active_days in self.num_active_days.items() if num_active_days >= self.min_active_days
        ]

        return (self.accounts
                .has_enabled_device()
                .filter(id__in=eligible_footprint_accounts)
                .filter(id__in=sufficiently_active_accounts)
                .exclude(id__in=earlier_recipients))

    def footprint_eligible(self, footprint):
        """Return true iff accounts with the given footprint are eligible for getting the prize."""
        eligible = footprint <= self.prize_threshold
        if self.next_prize_threshold is not None:
            eligible = eligible and footprint > self.next_prize_threshold
        return eligible

    @transaction.atomic
    def award_prize(self, account):
        message = f"Awarding prize {self.budget_level} to account {account.id} for month {self.prize_month_start}"
        if self.dry_run:
            print(message)
        else:
            logger.info(message)
            prize = Prize.objects.create(
                account=account,
                budget_level=self.budget_level,
                prize_month_start=self.prize_month_start
            )
            # TODO: Award all prizes in a single API call
            self.prize_api.award([prize])


@shared_task
def award_prizes(budget_level_identifier, next_budget_level_identifier=None, accounts=None, **kwargs):
    task = MonthlyPrizeTask(budget_level_identifier, next_budget_level_identifier, accounts=accounts, **kwargs)
    task.award_prizes()
