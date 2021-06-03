from datetime import timedelta
import logging
from celery import shared_task
from django.utils import timezone

from .processor import EventProcessor
from .models import Location


logger = logging.getLogger(__name__)
processor = EventProcessor()


@shared_task
def ingest_events():
    logger.info('Processing events')
    processor.process_events()


@shared_task
def cleanup():
    logger.info('Cleaning up')
    yesterday = timezone.now() - timedelta(days=1)
    # Delete locations that user has marked for deletion
    Location.objects.filter(deleted_at__isnull=False).filter(deleted_at__lte=yesterday).delete()
