import datetime
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from trips.models import Device
from .engine import NotificationEngine

logger = logging.getLogger(__name__)


def welcome_notification_devices(today):
    yesterday = today - datetime.timedelta(days=1)
    return Device.objects.filter(created_at__date__gte=yesterday, welcome_notification_sent=False)


@shared_task
def send_welcome_notifications(today=None):
    if today is None:
        today = timezone.now().date()
    logger.info("Sending welcome notifications")
    engine = NotificationEngine()
    for device in welcome_notification_devices(today):
        logger.debug(f"Sending notification to {device}")
        with transaction.atomic():
            device.welcome_notification_sent = True
            device.save(update_fields=['welcome_notification_sent'])
            # TODO: Use the actual title and content
            title = {lang: f'title {lang}' for lang in ('fi', 'en')}
            content = {lang: f'content {lang}' for lang in ('fi', 'en')}
            # TODO: We might want to call send_notification in batch, but then we need to figure out which notifications
            # have been sent successfully and set the welcome_notification_sent field for only those.
            engine.send_notification([device], title, content)


@shared_task
def send_monthly_summary_notifications(today):
    if today is None:
        today = timezone.now().date()
    logger.info("Sending monthly summary notifications")
    # In the Device model, we store always the first of the month
    this_month = today.replace(day=1)
    end_of_last_month = this_month - datetime.timedelta(days=1)
    last_month = end_of_last_month.replace(day=1)
    devices = Device.objects.filter(last_summary_notification_month=last_month)
    for device in devices:
        logger.debug(f"Sending notification to {device}")
        with transaction.atomic():
            device.last_summary_notification_month = last_month
            device.save(update_fields=['last_summary_notification_month'])
            # TODO: Send notification
