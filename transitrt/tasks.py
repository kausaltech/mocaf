import logging
from celery import shared_task
from django.conf import settings

from .siri_import import SiriImporter


logger = logging.getLogger(__name__)


@shared_task(ignore_result=True)
def fetch_siri_locations(importer_id):
    conf = settings.SIRI_IMPORTS[importer_id]
    importer = SiriImporter(agency_id=conf['agency_id'], url=conf['url'])
    logger.info('Reading transit locations for %s' % importer_id)
    importer.update_from_url()
