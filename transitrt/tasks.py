import logging
from transitrt.rt_import import make_importer
from celery import shared_task


logger = logging.getLogger(__name__)


importer_instances = {}


@shared_task(ignore_result=True)
def fetch_live_locations(importer_id):
    rt_importer = importer_instances.get(importer_id)
    if rt_importer is None:
        logger.info('Initializing transitrt importer: %s' % rt_importer)
        rt_importer = make_importer(importer_id)
        importer_instances[importer_id] = rt_importer

    logger.info('Reading transit locations for %s' % importer_id)
    rt_importer.update_from_url()
