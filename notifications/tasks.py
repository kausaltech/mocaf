import datetime
import logging
import random
import statistics
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import override
from importlib import import_module
from pprint import pprint

from budget.enums import TimeResolution, EmissionUnit
from budget.models import EmissionBudgetLevel, Prize
from budget.prize_api import PrizeApi
from trips.models import Device
from .engine import NotificationEngine
from .models import EventTypeChoices, NotificationLogEntry, NotificationTemplate

logger = logging.getLogger(__name__)

# Tasks usable in send_notification management command
registered_tasks = []


def register_for_management_command(cls):
    registered_tasks.append(cls)
    return cls


class NotificationTask:
    def __init__(self, event_type, now=None, engine=None, dry_run=False):
        if now is None:
            now = timezone.now()
        if engine is None:
            engine = NotificationEngine()

        self.event_type = event_type
        self.now = now
        self.engine = engine
        self.dry_run = dry_run

    def recipients(self):
        """Return the recipient devices for the notifications to be sent at `self.now`."""
        return Device.objects.filter(enabled_at__isnull=False)

    def contexts(self, device):
        """Return a dict mapping languages to a context for rendering notification templates for the given device."""
        return {language: {} for language, _ in settings.LANGUAGES}

    def random_template(self):
        templates = NotificationTemplate.objects.filter(event_type=self.event_type)
        try:
            return random.choice(templates)
        except IndexError:
            raise Exception(f"There is no notification template of type {self.event_type}.")

    def send_notifications(self, devices=None):
        """
        Send notifications to the given devices using a randomly chosen template of the proper event type.

        If `devices` is None, the recipients will the result of calling `recipients()`.
        """
        if devices is None:
            devices = self.recipients()

        logger.info(f"Sending {self.event_type} notifications")
        logger.debug(f"Sending notification to {len(devices)} devices")
        template = self.random_template()
        for device in devices:
            with transaction.atomic():
                self.before_notification_sent(device)
                contexts = self.contexts(device)
                title = template.render_all_languages('title', contexts)
                content = template.render_all_languages('body', contexts)
                if self.dry_run:
                    print(f"Sending notification to {device.uuid}:")
                    print("Title: ", end='')
                    pprint(title)
                    print("Content: ", end='')
                    pprint(content)
                    print()
                else:
                    NotificationLogEntry.objects.create(device=device, template=template, sent_at=self.now)
                    # TODO: Send to multiple devices at once (unless context is device-specific) by using a list of all
                    # devices as first argument of engine.send_notification()
                    response = self.engine.send_notification([device], title, content).json()
                    if not response['ok'] or response['message'] != 'success':
                        raise Exception("Sending notifications failed")

    def before_notification_sent(self, device):
        pass


@register_for_management_command
class WelcomeNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False):
        super().__init__(EventTypeChoices.WELCOME_MESSAGE, now, engine, dry_run)

    def recipients(self):
        """Return devices that signed up on the day preceding `self.now`."""
        # Don't send anything to devices that already got a welcome notification
        excluded_devices = (NotificationLogEntry.objects
                            .filter(template__event_type=self.event_type)
                            .values('device'))
        today = self.now.date()
        yesterday = today - datetime.timedelta(days=1)
        return (super().recipients()
                .filter(created_at__date__gte=yesterday)
                .exclude(id__in=excluded_devices))


class MonthlySummaryNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, prize_api=None, default_emissions=None, award_prizes=True):
        if getattr(self, 'event_type', None) is None:
            raise AttributeError("MonthlySummaryNotificationTask subclass must define event_type")

        super().__init__(self.event_type, now, engine, dry_run)

        if award_prizes and prize_api is None:
            prize_api = PrizeApi()
        self.prize_api = prize_api
        self.award_prizes = award_prizes

        one_month_ago = self.now - relativedelta(months=1)
        start_date = one_month_ago.date().replace(day=1)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_date = self.now.date().replace(day=1) - datetime.timedelta(days=1)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        self.summary_month_start = start_date

        # Update carbon footprints of all (enabled) devices to make sure there are no gaps on days without data
        devices = super().recipients()
        for device in devices:
            # We shouldn't call this if dry_run is True, but it probably doesn't break things if we do
            device.update_daily_carbon_footprint(start_datetime, end_datetime, default_emissions)
        self.footprints = {device: device.monthly_carbon_footprint(start_date) for device in devices}
        self.average_footprint = None
        if self.footprints:
            self.average_footprint = statistics.mean(self.footprints.values())

    def recipients(self):
        """Return devices that should receive a summary for the calendar month preceding the one of `self.now`."""
        today = self.now.date()
        this_month = today.replace(day=1)
        # Don't send anything to devices that already got a summary notification this month
        excluded_devices = (NotificationLogEntry.objects
                            .filter(template__event_type=self.event_type)
                            .filter(sent_at__date__gte=this_month)
                            .values('device'))

        eligible_devices = [dev.id for dev, footprint in self.footprints.items() if self.footprint_eligible(footprint)]

        return super().recipients().filter(id__in=eligible_devices).exclude(id__in=excluded_devices)

    def contexts(self, device):
        def rounded_float(f):
            return '%s' % int(float('%.3g' % f))
        contexts = super().contexts(device)
        for language, context in contexts.items():
            context['average_carbon_footprint'] = rounded_float(self.average_footprint)
            context['carbon_footprint'] = rounded_float(self.footprints[device])
            with override(language):
                context['month'] = date_format(self.summary_month_start, 'F')
        return contexts

    def footprint_eligible(self, footprint):
        """Return true iff devices with the given footprint are eligible for getting the notification."""
        return True

    @transaction.atomic
    def award_prize(self, device, budget_level):
        if self.award_prizes and self.dry_run:
            if self.dry_run:
                print(f"Awarding prize {budget_level} to device {device.uuid} for month {self.summary_month_start}")
            else:
                prize = Prize.objects.create(
                    device=device,
                    budget_level=budget_level,
                    prize_month_start=self.summary_month_start
                )
                # TODO: Award all prizes in a single API call
                self.prize_api.award([prize])


@register_for_management_command
class MonthlySummaryGoldNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_GOLD

    def __init__(self, now=None, engine=None, dry_run=False, prize_api=None, default_emissions=None, award_prizes=True):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            prize_api=prize_api,
            default_emissions=default_emissions,
            award_prizes=award_prizes
        )
        self.gold_level = EmissionBudgetLevel.objects.get(identifier='gold', year=self.summary_month_start.year)
        self.gold_threshold = self.gold_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        return footprint <= self.gold_threshold

    def before_notification_sent(self, device):
        assert self.footprints[device] <= self.gold_threshold
        self.award_prize(device, self.gold_level)


@register_for_management_command
class MonthlySummarySilverNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_SILVER

    def __init__(self, now=None, engine=None, dry_run=False, prize_api=None, default_emissions=None, award_prizes=True):
        super().__init__(
            now=now,
            engine=engine,
            prize_api=prize_api,
            dry_run=dry_run,
            default_emissions=default_emissions,
            award_prizes=award_prizes
        )
        self.silver_level = EmissionBudgetLevel.objects.get(identifier='silver', year=self.summary_month_start.year)
        self.gold_level = EmissionBudgetLevel.objects.get(identifier='gold', year=self.summary_month_start.year)
        self.silver_threshold = self.silver_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )
        self.gold_threshold = self.gold_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        return footprint <= self.silver_threshold and footprint > self.gold_threshold

    def before_notification_sent(self, device):
        assert self.footprints[device] <= self.silver_threshold and self.footprints[device] > self.gold_threshold
        self.award_prize(device, self.silver_level)


@register_for_management_command
class MonthlySummaryBronzeOrWorseNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_BRONZE_OR_WORSE

    def __init__(self, now=None, engine=None, dry_run=False, prize_api=None, default_emissions=None, award_prizes=True):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            prize_api=prize_api,
            default_emissions=default_emissions,
            award_prizes=award_prizes
        )
        self.bronze_level = EmissionBudgetLevel.objects.get(identifier='bronze', year=self.summary_month_start.year)
        self.silver_level = EmissionBudgetLevel.objects.get(identifier='silver', year=self.summary_month_start.year)
        self.bronze_threshold = self.bronze_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )
        self.silver_threshold = self.silver_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        # Anything worse than silver gets a notification even if not within bronze level
        return footprint > self.silver_threshold

    def before_notification_sent(self, device):
        assert self.footprint_eligible(self.footprints[device])
        # Anything worse than silver gets a notification, but we only want to give prizes within bronze level
        if self.footprints[device] <= self.bronze_threshold:
            self.award_prize(device, self.bronze_level)


@register_for_management_command
class NoRecentTripsNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False):
        super().__init__(EventTypeChoices.NO_RECENT_TRIPS, now, engine, dry_run)

    def recipients(self):
        """Return devices that have not had any trips in 14 days until `self.now`."""
        # Don't send anything to devices that already got a no-recent-trips notification in the last 30 days
        avoid_duplicates_after = self.now - datetime.timedelta(days=30)
        already_notified_devices = (NotificationLogEntry.objects
                                    .filter(template__event_type=self.event_type)
                                    .filter(sent_at__gte=avoid_duplicates_after)
                                    .values('device'))
        inactivity_threshold = self.now - datetime.timedelta(days=14)
        devices_with_recent_trips = (Device.objects
                                     .filter(trips__legs__end_time__gte=inactivity_threshold)
                                     .values('id'))
        return (super().recipients()
                .exclude(id__in=devices_with_recent_trips)
                .exclude(id__in=already_notified_devices))


@shared_task
def send_notifications(task_class, devices=None, **kwargs):
    if isinstance(task_class, str):
        task_class = import_module(task_class)
        parts = task_class.split('.')
        class_name = parts.pop(-1)
        module = import_module('.'.join(parts))
        task_class = getattr(module, class_name)
    task = task_class(**kwargs)
    task.send_notifications(devices)
