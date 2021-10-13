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
from budget.models import EmissionBudgetLevel
from budget.tasks import MonthlyPrizeTask
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
    def __init__(self, event_type, now=None, engine=None, dry_run=False, devices=None, force=False):
        """
        `devices` can be set to a QuerySet smaller than Device.objects.all() to limit the potential recipients.
        If `force` is True, attempt to send the notification to all devices in `devices` (or all if `devices` is not
        set) regardless of whether they qualify for the notification.
        """
        if now is None:
            now = timezone.now()
        if engine is None:
            engine = NotificationEngine()
        if devices is None:
            devices = Device.objects.all()

        self.event_type = event_type
        self.now = now
        self.engine = engine
        self.dry_run = dry_run
        self.devices = devices
        self.force = force

    def recipients(self):
        """Return the recipient devices for the notifications to be sent at `self.now`."""
        return self.devices.enabled()

    def contexts(self, device):
        """Return a dict mapping languages to a context for rendering notification templates for the given device."""
        return {language: {} for language, _ in settings.LANGUAGES}

    def random_template(self):
        templates = NotificationTemplate.objects.filter(event_type=self.event_type)
        try:
            return random.choice(templates)
        except IndexError:
            raise Exception(f"There is no notification template of type {self.event_type}.")

    def send_notifications(self):
        """Send notifications using a randomly chosen template of the proper event type."""
        if self.force:
            recipients = self.devices
        else:
            recipients = self.recipients()
        logger.info(f"Sending {self.event_type} notifications")
        logger.debug(f"Sending notification to {len(recipients)} devices")
        template = self.random_template()
        for device in recipients:
            with transaction.atomic():
                contexts = self.contexts(device)
                title = template.render_all_languages('title', contexts)
                content = template.render_all_languages('body', contexts)
                if self.dry_run:
                    print(f"Sending notification to {device.uuid}")
                    print("Title:")
                    pprint(title)
                    print("Content:")
                    pprint(content)
                    print()
                else:
                    logger.info(f"Sending notification to {device.uuid}")
                    NotificationLogEntry.objects.create(device=device, template=template, sent_at=self.now)
                    # TODO: Send to multiple devices at once (unless context is device-specific) by using a list of all
                    # devices as first argument of engine.send_notification()
                    response = self.engine.send_notification([device], title, content).json()
                    if not response['ok'] or response['message'] != 'success':
                        raise Exception("Sending notifications failed")


@register_for_management_command
class WelcomeNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False):
        super().__init__(EventTypeChoices.WELCOME_MESSAGE, now, engine, dry_run, devices, force)

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
    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        """
        If `restrict_average` is True, consider only devices in `devices` for the average footprint and only regenerate
        the carbon footprints for these. (Useful for testing since regenerating footprints is expensive.)
        `min_active_days` is the number of days of the relevant month that the device must have been active in order to
        receive a notification.
        """
        if getattr(self, 'event_type', None) is None:
            raise AttributeError("MonthlySummaryNotificationTask subclass must define event_type")

        super().__init__(self.event_type, now, engine, dry_run, devices, force)
        self.min_active_days = min_active_days

        one_month_ago = self.now - relativedelta(months=1)
        start_date = one_month_ago.date().replace(day=1)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_date = self.now.date().replace(day=1) - datetime.timedelta(days=1)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)
        self.summary_month_start = start_date
        self.summary_month_end = end_date

        # Update carbon footprints of all relevant devices to make sure there are no gaps on days without data
        if restrict_average:
            qs = devices
        else:
            qs = Device.objects.all()

        device_universe = qs.has_trips_during(start_date, end_date)

        for device in device_universe:
            # We shouldn't call this if dry_run is True, but it probably doesn't break things if we do
            device.update_daily_carbon_footprint(start_datetime, end_datetime, default_emissions)
        self.footprints = {device: device.monthly_carbon_footprint(start_date) for device in device_universe}
        self.average_footprint = None
        if self.footprints:
            self.average_footprint = statistics.mean(self.footprints.values())
        self.num_active_days = {device: device.num_active_days(start_date) for device in device_universe}

    def recipients(self):
        """Return devices that should receive a summary for the calendar month preceding the one of `self.now`."""
        today = self.now.date()
        this_month = today.replace(day=1)
        # Don't send anything to devices that already got a summary notification this month
        earlier_recipients = (NotificationLogEntry.objects
                              .filter(template__event_type=self.event_type)
                              .filter(sent_at__date__gte=this_month)
                              .values('device'))

        eligible_footprint_devices = [
            dev.id for dev, footprint in self.footprints.items() if self.footprint_eligible(footprint)
        ]

        sufficiently_active_devices = [
            dev.id for dev, num_active_days in self.num_active_days.items() if num_active_days >= self.min_active_days
        ]

        return (super().recipients()
                .filter(id__in=eligible_footprint_devices)
                .filter(id__in=sufficiently_active_devices)
                .exclude(id__in=earlier_recipients))

    def contexts(self, device):
        def rounded_float(f):
            return '%s' % int(float('%.3g' % f))
        contexts = super().contexts(device)
        for language, context in contexts.items():
            context['average_carbon_footprint'] = rounded_float(self.average_footprint)
            # FIXME: The commented-out line reports the footprint as used for prize determination. However, in the app,
            # device.get_carbon_footprint_summary() is used for the footprint and this does not fill in "default
            # emissions" for days without any data. So the numbers differ. Ideally, the app should display the corrected
            # footprint (i.e., containing the filled-in value), but it does not for now.
            # context['carbon_footprint'] = rounded_float(self.footprints[device])
            footprint_summary = device.get_carbon_footprint_summary(
                self.summary_month_start,
                self.summary_month_end,
                time_resolution=TimeResolution.MONTH,
                units=EmissionUnit.KG,
            )
            if not footprint_summary:
                carbon_footprint = 0.0
            else:
                assert len(footprint_summary) == 1
                footprint_summary = footprint_summary[0]
                assert footprint_summary['date'] == self.summary_month_start
                carbon_footprint = footprint_summary['carbon_footprint']
            context['carbon_footprint'] = rounded_float(carbon_footprint)
            with override(language):
                context['month'] = date_format(self.summary_month_start, 'F')
        return contexts

    def footprint_eligible(self, footprint):
        """Return true iff devices with the given footprint are eligible for getting the notification."""
        return True


@register_for_management_command
class MonthlySummaryGoldNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_GOLD

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
        )
        self.gold_level = EmissionBudgetLevel.objects.get(identifier='gold', year=self.summary_month_start.year)
        self.gold_threshold = self.gold_level.calculate_for_date(
            self.summary_month_start, TimeResolution.MONTH, EmissionUnit.KG
        )

    def footprint_eligible(self, footprint):
        return footprint <= self.gold_threshold


@register_for_management_command
class MonthlySummarySilverNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_SILVER

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
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


@register_for_management_command
class MonthlySummaryBronzeOrWorseNotificationTask(MonthlySummaryNotificationTask):
    event_type = EventTypeChoices.MONTHLY_SUMMARY_BRONZE_OR_WORSE

    def __init__(
        self, now=None, engine=None, dry_run=False, devices=None, force=False, default_emissions=None,
        restrict_average=False, min_active_days=0
    ):
        super().__init__(
            now=now,
            engine=engine,
            dry_run=dry_run,
            devices=devices,
            force=force,
            default_emissions=default_emissions,
            restrict_average=restrict_average,
            min_active_days=min_active_days,
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


@register_for_management_command
class NoRecentTripsNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None, dry_run=False, devices=None, force=False):
        super().__init__(EventTypeChoices.NO_RECENT_TRIPS, now, engine, dry_run, devices, force)

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
    task = task_class(devices=devices, **kwargs)
    task.send_notifications()


@shared_task
def award_prizes_and_send_notifications(devices=None, **kwargs):
    MonthlyPrizeTask('bronze', 'silver', devices=devices, **kwargs).award_prizes()
    MonthlyPrizeTask('silver', 'gold', devices=devices, **kwargs).award_prizes()
    MonthlyPrizeTask('gold', devices=devices, **kwargs).award_prizes()
    MonthlySummaryBronzeOrWorseNotificationTask(devices=devices, **kwargs).send_notifications()
    MonthlySummarySilverNotificationTask(devices=devices, **kwargs).send_notifications()
    MonthlySummaryGoldNotificationTask(devices=devices, **kwargs).send_notifications()
