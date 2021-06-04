import datetime
import logging
import random
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from trips.models import Device
from .engine import NotificationEngine
from .models import EventTypeChoices, NotificationLogEntry, NotificationTemplate

logger = logging.getLogger(__name__)


def welcome_notification_devices(today: datetime.date):
    """Return devices that should receive a welcome notification because they signed up one day before `today`."""
    excluded_devices = (NotificationLogEntry.objects
                        .filter(template__event_type=EventTypeChoices.WELCOME_MESSAGE)
                        .values('device'))
    yesterday = today - datetime.timedelta(days=1)
    return Device.objects.filter(created_at__date__gte=yesterday).exclude(id__in=excluded_devices)


def monthly_summary_notification_devices(today: datetime.date):
    """Return devices that should receive a summary notification for the calendar month preceding the one of `today`."""
    this_month = today.replace(day=1)
    excluded_devices = (NotificationLogEntry.objects
                        .filter(template__event_type=EventTypeChoices.MONTHLY_SUMMARY)
                        .filter(sent_at__date__gte=this_month)
                        .values('device'))
    return Device.objects.exclude(id__in=excluded_devices)


def random_template(event_type):
    templates = NotificationTemplate.objects.filter(event_type=event_type)
    try:
        return random.choice(templates)
    except IndexError:
        raise Exception(f"There is no notification template of type {event_type}.")


@shared_task
def send_welcome_notifications(now=None):
    if now is None:
        now = timezone.now()
    today = now.date()
    logger.info("Sending welcome notifications")
    engine = NotificationEngine()
    template = random_template(EventTypeChoices.WELCOME_MESSAGE)

    devices = welcome_notification_devices(today)
    logger.debug(f"Sending notification to {len(devices)} devices")
    with transaction.atomic():
        for device in devices:
            NotificationLogEntry.objects.create(device=device, template=template, sent_at=now)
        title = template.render_all_languages('title')
        content = template.render_all_languages('body')
        response = engine.send_notification(devices, title, content)
        if not response['ok'] or response['message'] != 'success':
            raise Exception("Sending notifications failed")


@shared_task
def send_monthly_summary_notifications(now=None):
    if now is None:
        now = timezone.now()
    today = now.date()
    logger.info("Sending monthly summary notifications")
    engine = NotificationEngine()
    template = random_template(EventTypeChoices.MONTHLY_SUMMARY)

    this_month = today.replace(day=1)
    end_of_last_month = this_month - datetime.timedelta(days=1)
    last_month = end_of_last_month.replace(day=1)

    for device in monthly_summary_notification_devices(last_month):
        logger.debug(f"Sending notification to {device}")
        with transaction.atomic():
            NotificationLogEntry.objects.create(device=device, template=template, sent_at=now)
            title = template.render_all_languages('title')
            content = template.render_all_languages('body')
            engine.send_notification([device], title, content)
