import logging
from celery import shared_task

from .processor import EventProcessor


logger = logging.getLogger(__name__)
processor = EventProcessor()


@shared_task
def ingest_events():
    logger.info('Processing events')
    processor.process_events()
