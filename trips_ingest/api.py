import json
import logging

import sentry_sdk
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

    uid = data.get('uid')
    if not isinstance(uid, str):
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
    if dev.debug_log_level or dev.custom_config:
        if not dev.debugging_enabled_at:
            dev.debugging_enabled_at = timezone.now()
            dev.save(update_fields=['debugging_enabled_at'])
            logger.info('Enabling debug logs or custom config for %s' % uid)

        config = {
            'autoSyncThreshold': 500,
            'desiredOdometerAccuracy': 10,
            'deferTime': 120000,
            'elasticityMultiplier': 4,
            'motionTriggerDelay': 30000,
            'maxBatchSize': 500,
            'locationUpdateInterval': 5000,
            'heartbeatInterval': 120 * 60,
            'preventSuspend': False,
        }

        if dev.custom_config and isinstance(dev.custom_config, dict):
            config.update(dev.custom_config)

        if dev.debug_log_level:
            endpoint_path = reverse('upload-debug-log', kwargs={'uuid': uid})
            abs_path = request.build_absolute_uri(endpoint_path)
            c.append(['uploadLog', abs_path])
            c.append(['destroyLog'])
            config['logLevel'] = dev.debug_log_level
            logger.info('Requesting log upload for %s' % uid)

        c.append(['setConfig', config])
    else:
        if dev.debugging_enabled_at:
            c.append(['setConfig', {'logLevel': 0}])
            c.append(['destroyLog'])
            dev.debugging_enabled_at = None
            dev.save(update_fields=['debugging_enabled_at'])

    if c:
        resp.clear()
        resp['background_geolocation'] = c


@api_view(['POST'])
@schema(None)
def ingest_view(request):
    received_at = timezone.now()
    data = request.data
    obj = ReceiveData(data=data, received_at=received_at)
    try:
        obj.device = Device.objects.get(uuid=obj.get_uuid())
    except Exception as e:
        sentry_sdk.capture_exception(e)
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
    for key, val in list(data.items()):
        if isinstance(val, list) and len(val) == 1:
            val = val[0]
        if key == 'state' and isinstance(val, str):
            try:
                val = json.loads(val)
            except Exception:
                pass
        data[key] = val

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
