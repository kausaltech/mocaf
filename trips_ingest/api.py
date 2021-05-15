import logging
from django.utils import timezone
from django.urls import reverse
from rest_framework.decorators import api_view, schema
from django.http import HttpResponse
from rest_framework.response import Response

from trips.models import Device
from .models import ReceiveData, ReceiveDebugLog


logger = logging.getLogger(__name__)


def modify_for_debug_logs(request, data, resp):
    if not isinstance(data, dict):
        return
    loc_data = data.get('location')
    if not isinstance(loc_data, list):
        return
    if len(loc_data) < 1:
        return
    extra_data = loc_data[0].get('extras')
    if not isinstance(extra_data, dict):
        return

    uid = extra_data.get('uid', None)
    if not isinstance(uid, str):
        return

    try:
        dev = Device.objects.get(uuid=uid)
    except Exception:
        return

    c = []
    if dev.debug_log_level:
        if not dev.debugging_enabled_at:
            c.append(['setConfig', {'logLevel': dev.debug_log_level}])
            dev.debugging_enabled_at = timezone.now()
            dev.save(update_fields=['debugging_enabled_at'])
            logger.info('Enabling debug logs for %s' % uid)
        else:
            endpoint_path = reverse('upload-debug-log', kwargs={'uuid': uid})
            abs_path = request.build_absolute_uri(endpoint_path)
            c.append(['uploadLog', abs_path])
            logger.info('Requesting log upload for %s' % uid)
    else:
        if dev.debugging_enabled_at:
            c.append(['setConfig', {'logLevel': 0}])
            c.append(['destroyLog'])

    if c:
        resp.clear()
        resp['background_geolocation'] = c


@api_view(['POST'])
@schema(None)
def ingest_view(request):
    received_at = timezone.now()
    data = request.data
    obj = ReceiveData(data=data, received_at=received_at)
    obj.save()

    resp = {'ok': True, 'received_at': received_at}
    modify_for_debug_logs(request, data, resp)
    return Response(resp)


def upload_log_view(request, uuid):
    logger.info('Received debug log for uuid %s' % uuid)

    if request.method != 'POST':
        logger.error('Not a POST request')
        return HttpResponse()

    dev = Device.objects.filter(uuid=uuid).first()
    if dev is None:
        logger.error('Device not found: %s' % uuid)
        return HttpResponse()
    if not dev.debug_log_level:
        logger.error('Debug logging not enabled for device: %s' % uuid)
        return HttpResponse()

    received_at = timezone.now()
    data = dict(request.POST) if request.POST else {}
    obj = ReceiveDebugLog(data=data, received_at=received_at, uuid=uuid)

    if request.FILES:
        log_file = list(request.FILES.values())[0]
        if log_file.size > 2000000:
            logger.error('Upload file too big: %d' % log_file.size)
            return HttpResponse()
        obj.log = log_file.read()
    else:
        logger.warn('No debug log for uuid %s' % uuid)
    obj.save()
    logger.info('Log successfully saved for uuid %s' % uuid)
    return HttpResponse()
