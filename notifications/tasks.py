import datetime
import logging
import random
import statistics
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
    def __init__(self, event_type, now=None, engine=None):
        if now is None:
            now = timezone.now()
        if engine is None:
            engine = NotificationEngine()

        self.event_type = event_type
        self.now = now
        self.engine = engine

    def recipients(self):
        """Return the recipient devices for the notifications to be sent at `self.now`."""
        return Device.objects.filter(enabled_at__isnull=False)

    def context(self, device):
        """Return the context for rendering notification templates for the given device."""
        return {}

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
        with transaction.atomic():
            for device in devices:
                NotificationLogEntry.objects.create(device=device, template=template, sent_at=self.now)
                context = self.context(device)
                title = template.render_all_languages('title', **context)
                content = template.render_all_languages('body', **context)
                # TODO: Send to multiple devices at once (unless context is device-specific) by using a list of all
                # devices as first argument of engine.send_notification()
                response = self.engine.send_notification([device], title, content)
                if not response['ok'] or response['message'] != 'success':
                    raise Exception("Sending notifications failed")


class WelcomeNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None):
        super().__init__(EventTypeChoices.WELCOME_MESSAGE, now, engine)

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
    def __init__(self, now=None, engine=None):
        super().__init__(EventTypeChoices.MONTHLY_SUMMARY, now, engine)

        one_month_ago = self.now - relativedelta(months=1)
        start_date = one_month_ago.date().replace(day=1)
        start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
        end_date = self.now.date().replace(day=1) - datetime.timedelta(days=1)
        end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

        # Update carbon footprints of all (enabled) devices to make sure there are no gaps on days without data
        devices = super().recipients()
        for device in devices:
            device.update_daily_carbon_footprint(start_datetime, end_datetime)
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
        return super().recipients().exclude(id__in=excluded_devices)

    def context(self, device):
        def rounded_float(f):
            return '%s' % int(float('%.3g' % f))
        return {
            'carbon_footprint': rounded_float(self.footprints[device]),
            'average_carbon_footprint': rounded_float(self.average_footprint),
        }


class NoRecentTripsNotificationTask(NotificationTask):
    def __init__(self, now=None, engine=None):
        super().__init__(EventTypeChoices.NO_RECENT_TRIPS, now, engine)

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
def send_notifications(task_class, now=None, devices=None, engine=None):
    if isinstance(task_class, str):
        task_class = import_module(task_class)
        parts = task_class.split('.')
        class_name = parts.pop(-1)
        module = import_module('.'.join(parts))
        task_class = getattr(module, class_name)
    task = task_class(now=now, engine=engine)
    task.send_notifications(devices)
