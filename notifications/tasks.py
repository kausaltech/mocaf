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


@shared_task
def send_welcome_notifications(today=None):
    if today is None:
        today = timezone.now().date()
    logger.info("Sending welcome notifications")
    engine = NotificationEngine()

    templates = NotificationTemplate.objects.filter(event_type=EventTypeChoices.WELCOME_MESSAGE)
    try:
        template = random.choice(templates)
    except IndexError:
        raise Exception("There is no welcome message template.")

    devices = welcome_notification_devices(today)
    logger.debug(f"Sending notification to {len(devices)} devices")
    with transaction.atomic():
        for device in devices:
            device.welcome_notification_sent = True
        Device.objects.bulk_update(devices, ['welcome_notification_sent'])
        title = {lang: getattr(template, build_localized_fieldname('title', lang)) for lang in ('fi', 'en')}
        content = {lang: getattr(template, build_localized_fieldname('body', lang)) for lang in ('fi', 'en')}
        response = engine.send_notification(devices, title, content)
        if not response['ok'] or response['message'] != 'success':
            raise Exception("Sending notifications failed")


@shared_task
def send_monthly_summary_notifications(today):
    if today is None:
        today = timezone.now().date()
    logger.info("Sending monthly summary notifications")
    engine = NotificationEngine()

    # In the Device model, we store always the first of the month
    this_month = today.replace(day=1)
    end_of_last_month = this_month - datetime.timedelta(days=1)
    last_month = end_of_last_month.replace(day=1)

    for device in monthly_summary_notification_devices(last_month):
        logger.debug(f"Sending notification to {device}")
        with transaction.atomic():
            device.last_summary_notification_month = last_month
            device.save(update_fields=['last_summary_notification_month'])
            # TODO: Use the actual title and content
            title = {lang: f'title {lang}' for lang in ('fi', 'en')}
            content = {lang: f'content {lang}' for lang in ('fi', 'en')}
            engine.send_notification([device], title, content)
