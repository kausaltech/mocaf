from datetime import timedelta
import logging
from celery import shared_task
from django.utils import timezone
from django.db import connection

from trips.models import LegLocation

from .processor import EventProcessor
from .models import Location, ReceiveData, SensorSample


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
    ret = Location.objects.filter(deleted_at__isnull=False).filter(deleted_at__lte=yesterday).delete()
    logger.info('Locations cleaned: %s' % str(ret))
    # Delete expired leg locations
    ret = LegLocation.objects.expired(buffer_hours=48).delete()
    logger.info('Leg locations cleaned: %s' % str(ret))
    # Drop stale chunks in hypertables
    with connection.cursor() as cursor:
        cursor.execute('''SELECT drop_chunks('trips_ingest_location', older_than => interval '2 week')''')
        cursor.execute('''SELECT drop_chunks('transitrt_vehiclelocation', older_than => interval '2 week')''')

    logger.info('Hypertables cleaned')

    # Clean up ingest buffers
    two_weeks_ago = timezone.now() - timedelta(days=14)
    ret = ReceiveData.objects.filter(received_at__lte=two_weeks_ago).delete()
    logger.info('Ingest receive data cleaned: %s' % str(ret))

    SensorSample.objects.filter(time__lte=two_weeks_ago).delete()
    logger.info('Sensor samples cleaned: %s' % str(ret))
