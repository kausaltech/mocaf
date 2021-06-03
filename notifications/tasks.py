import datetime
import logging
import random
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from modeltrans.utils import build_localized_fieldname

from trips.models import Device
from .engine import NotificationEngine
from .models import EventTypeChoices, NotificationTemplate

logger = logging.getLogger(__name__)


def welcome_notification_devices(today: datetime.date):
    """Return devices that should receive a welcome notification because they signed up one day before `today`"""
    yesterday = today - datetime.timedelta(days=1)
    return Device.objects.filter(created_at__date__gte=yesterday, welcome_notification_sent=False)


def monthly_summary_notification_devices(summary_month: datetime.date):
    """Return devices that should receive a summary notification for the given month"""
    # Return devices whose last summary notification concerned some month before summary_month
    return Device.objects.exclude(last_summary_notification_month__gte=summary_month)


def random_template(event_type):
    templates = NotificationTemplate.objects.filter(event_type=event_type)
    try:
        return random.choice(templates)
    except IndexError:
        raise Exception(f"There is no notification template of type {event_type}.")


@shared_task
def send_welcome_notifications(today=None):
    if today is None:
        today = timezone.now().date()
    logger.info("Sending welcome notifications")
    engine = NotificationEngine()
    template = random_template(EventTypeChoices.WELCOME_MESSAGE)

    devices = welcome_notification_devices(today)
    logger.debug(f"Sending notification to {len(devices)} devices")
    with transaction.atomic():
        for device in devices:
            device.welcome_notification_sent = True
        Device.objects.bulk_update(devices, ['welcome_notification_sent'])
        title = template.render_all_languages('title')
        content = template.render_all_languages('body')
        response = engine.send_notification(devices, title, content)
        if not response['ok'] or response['message'] != 'success':
            raise Exception("Sending notifications failed")


@shared_task
def send_monthly_summary_notifications(today):
    if today is None:
        today = timezone.now().date()
    logger.info("Sending monthly summary notifications")
    engine = NotificationEngine()
    template = random_template(EventTypeChoices.MONTHLY_SUMMARY)

    # In the Device model, we store always the first of the month
    this_month = today.replace(day=1)
    end_of_last_month = this_month - datetime.timedelta(days=1)
    last_month = end_of_last_month.replace(day=1)

    for device in monthly_summary_notification_devices(last_month):
        logger.debug(f"Sending notification to {device}")
        with transaction.atomic():
            device.last_summary_notification_month = last_month
            device.save(update_fields=['last_summary_notification_month'])
            title = template.render_all_languages('title')
            content = template.render_all_languages('body')
            engine.send_notification([device], title, content)
