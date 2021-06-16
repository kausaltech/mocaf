import datetime
import logging
import random
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone
from importlib import import_module

from trips.models import Device
from .engine import NotificationEngine
from .models import EventTypeChoices, NotificationLogEntry, NotificationTemplate

logger = logging.getLogger(__name__)


class NotificationTask:
    def __init__(self, event_type, engine=None):
        if engine is None:
            engine = NotificationEngine()

        self.event_type = event_type
        self.engine = engine

    def recipients(self, now):
        """Return the recipient devices for the notifications to be sent at `now`."""
        raise NotImplementedError()

    def random_template(self):
        templates = NotificationTemplate.objects.filter(event_type=self.event_type)
        try:
            return random.choice(templates)
        except IndexError:
            raise Exception(f"There is no notification template of type {self.event_type}.")

    def send_notifications(self, now=None, devices=None):
        """
        Send notifications to the given devices using a randomly chosen template of the proper event type.

        If `devices` is None, the recipients will the result of calling `recipients()`.
        """
        if now is None:
            now = timezone.now()
        if devices is None:
            devices = self.recipients(now)

        logger.info(f"Sending {self.event_type} notifications")
        logger.debug(f"Sending notification to {len(devices)} devices")
        template = self.random_template()
        with transaction.atomic():
            for device in devices:
                NotificationLogEntry.objects.create(device=device, template=template, sent_at=now)
            title = template.render_all_languages('title')
            content = template.render_all_languages('body')
            response = self.engine.send_notification(devices, title, content)
            if not response['ok'] or response['message'] != 'success':
                raise Exception("Sending notifications failed")


class WelcomeNotificationTask(NotificationTask):
    def __init__(self, engine=None):
        super().__init__(EventTypeChoices.WELCOME_MESSAGE, engine)

    def recipients(self, now):
        """Return devices that signed up on the day preceding `now`."""
        # Don't send anything to devices that already got a welcome notification
        excluded_devices = (NotificationLogEntry.objects
                            .filter(template__event_type=self.event_type)
                            .values('device'))
        today = now.date()
        yesterday = today - datetime.timedelta(days=1)
        return (Device.objects
                .filter(created_at__date__gte=yesterday)
                .exclude(id__in=excluded_devices))


class MonthlySummaryNotificationTask(NotificationTask):
    def __init__(self, engine=None):
        super().__init__(EventTypeChoices.MONTHLY_SUMMARY, engine)

    def recipients(self, now):
        """Return devices that should receive a summary for the calendar month preceding the one of `now`."""
        today = now.date()
        this_month = today.replace(day=1)
        # Don't send anything to devices that already got a summary notification this month
        excluded_devices = (NotificationLogEntry.objects
                            .filter(template__event_type=self.event_type)
                            .filter(sent_at__date__gte=this_month)
                            .values('device'))
        return Device.objects.exclude(id__in=excluded_devices)

    def send_notifications(self, now=None, devices=None):
        # Update carbon footprints of all devices to make sure there are no gaps on days without data
        start_time = self.summary_month_start_datetime(now)
        end_time = self.summary_month_end_datetime(now)
        for device in Device.objects.all():
            device.update_daily_carbon_footprint(start_time, end_time)
        super().send_notifications(now=now, devices=devices)

    # TODO: Write tests for the following methods
    def summary_month_start_date(self, now):
        one_month_ago = now - relativedelta(months=1)
        return one_month_ago.date().replace(day=1)

    def summary_month_start_datetime(self, now):
        start_date = self.summary_month_start_date(now)
        return datetime.datetime.combine(start_date, datetime.time.min)

    def summary_month_end_date(self, now):
        return now.date().replace(day=1) - datetime.timedelta(days=1)

    def summary_month_end_datetime(self, now):
        end_date = self.summary_month_end_date(now)
        return datetime.datetime.combine(end_date, datetime.time.max)


class NoRecentTripsNotificationTask(NotificationTask):
    def __init__(self, engine=None):
        super().__init__(EventTypeChoices.NO_RECENT_TRIPS, engine)

    def recipients(self, now):
        """Return devices that have not had any trips in 14 days until `now`."""
        # Don't send anything to devices that already got a no-recent-trips notification in the last 30 days
        avoid_duplicates_after = now - datetime.timedelta(days=30)
        already_notified_devices = (NotificationLogEntry.objects
                                    .filter(template__event_type=self.event_type)
                                    .filter(sent_at__gte=avoid_duplicates_after)
                                    .values('device'))
        inactivity_threshold = now - datetime.timedelta(days=14)
        devices_with_recent_trips = (Device.objects
                                     .filter(trips__legs__end_time__gte=inactivity_threshold)
                                     .values('id'))
        return (Device.objects
                .exclude(id__in=devices_with_recent_trips)
                .exclude(id__in=already_notified_devices))


@shared_task
def send_notifications(task_class, now=None, devices=None, engine=None):
    if isinstance(task_class, str):
        task_class = import_module(task_class)
        parts = task_class.split('.')
        class_name = parts.pop(-1)
        module = import_module('.'.join(parts))
        task_class = getattr(module, class_name)
    if now is None:
        now = timezone.now()
    task = task_class(engine=engine)
    task.send_notifications(now, devices)
