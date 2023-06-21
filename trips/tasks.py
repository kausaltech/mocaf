import logging
from celery import shared_task

from .generate import TripGenerator


logger = logging.getLogger(__name__)
generator = TripGenerator()


@shared_task
def generate_new_trips():
    logger.info('Generating new trips')
    generator.generate_new_trips()
