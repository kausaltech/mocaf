import uuid
import pytz
from datetime import datetime, timedelta
from pprint import pprint
import logging

from dateutil.parser import isoparse
import sentry_sdk
from django.db import transaction
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from calc.trips import LOCAL_2D_CRS
from trips.models import Device
from .models import ReceiveData, Location, DeviceHeartbeat, ActivityTypeChoices


logger = logging.getLogger(__name__)

ACTIVITY_TYPES = set([x.value for x in list(ActivityTypeChoices)])

LOCAL_CRS = SpatialReference(LOCAL_2D_CRS)
GPS_CRS = SpatialReference(4326)
coord_transform = CoordTransform(GPS_CRS, LOCAL_CRS)


def null_float(val):
    if val is None or val == -1:
        return None
    return float(val)


class InvalidEventError(Exception):
    pass


def uuid_or_bye(val):
    try:
        uid = uuid.UUID(val)
    except Exception:
        raise InvalidEventError('invalid uuid')
    return uid


def sane_time_or_bye(dt):
    now = timezone.now()
    if dt < now - timedelta(days=7):
        raise InvalidEventError('time is too much in the past')
    if dt > now + timedelta(minutes=5):
        raise InvalidEventError('time is too much in the future')
    return dt


class EventProcessor:
    def __init__(self):
        pass

    def mark_imported(self, event, failed=False):
        event.import_failed = failed
        event.imported_at = timezone.now()
        event.save(update_fields=['import_failed', 'imported_at'])

    def process_location_event(self, event):
        locs = event.data.get('location')
        if not isinstance(locs, list):
            raise InvalidEventError("location missing or invalid")

        DICT_KEYS = ['activity', 'coords', 'extras']
        last_uuid = None
        for loc in locs:
            for key in DICT_KEYS:
                if not isinstance(loc.get(key), dict):
                    raise InvalidEventError("location.%s missing or invalid" % key)

            obj = Location(created_at=event.received_at)

            try:
                dt = isoparse(loc.get('timestamp'))
            except Exception as e:
                raise InvalidEventError("location has invalid time")

            obj.time = sane_time_or_bye(dt)
            obj.uuid = uuid_or_bye(loc['extras'].get('uid'))

            if Location.objects.filter(time=obj.time, uuid=obj.uuid).exists():
                logger.warning('Location for %s at %s already exists' % (obj.uuid, obj.time))
                return

            last_uuid = obj.uuid

            atype = loc['activity'].get('type')
            if atype not in ACTIVITY_TYPES:
                raise InvalidEventError("invalid activity type")
            obj.atype = atype
            obj.aconf = null_float(loc['activity'].get('confidence'))

            heading = null_float(loc['coords'].get('heading'))
            if heading is not None and heading > 360:
                raise InvalidEventError("invalid heading")
            obj.heading = heading
            obj.heading_error = null_float(loc['coords'].get('heading_accuracy'))
            obj.altitude = null_float(loc['coords'].get('altitude'))
            obj.altitude_accuracy = null_float(loc['coords'].get('altitude_accuracy'))
            obj.speed = null_float(loc['coords'].get('speed'))
            obj.speed_error = null_float(loc['coords'].get('speed_accuracy'))
            obj.odometer = null_float(loc.get('odometer'))
            obj.loc_error = null_float(loc['coords'].get('accuracy'))

            point = Point(loc['coords']['longitude'], loc['coords']['latitude'], srid=LOCAL_2D_CRS)
            point.transform(coord_transform)
            if point.x <= 0 or point.y <= 0:
                raise InvalidEventError("invalid coords")
            obj.loc = point

            obj.debug = bool(loc['extras'].get('debug', 0))
            obj.is_moving = loc.get('is_moving')
            obj.battery_charging = loc.get('battery', {}).get('is_charging')
            obj.save(force_insert=True)

        logger.info('%d location samples saved for %s' % (len(locs), last_uuid))

    def process_device_info_event(self, event):
        data = event.data

        uid = uuid_or_bye(data.get('userId'))

        dev = Device.objects.filter(uuid=uid).first()
        if dev is None:
            dev = Device(uuid=uid)
        dev.brand = data.get('brand')
        dev.model = data.get('model')
        dev.platform = data.get('os')
        dev.system_version = data.get('systemVersion')
        dev.save()

    def process_heartbeat_event(self, event):
        data = event.data
        dt = datetime.fromtimestamp(data.get('time') / 1000, pytz.utc)
        uid = uuid_or_bye(data.get('userId'))
        time = sane_time_or_bye(dt)
        if DeviceHeartbeat.objects.filter(time=time, uuid=uid).exists():
            logger.warning('Heartbeat for %s at %s already exists' % (uid, time))
            return

        obj = DeviceHeartbeat(time=sane_time_or_bye(dt), uuid=uid, created_at=event.received_at)
        obj.save(force_insert=True)

    def process_sensor_event(self, event):
        # Discard for now
        pass

    def process_event(self, event):
        data = event.data
        data_type = data.get('dataType')
        if data_type is None and 'location' in data:
            data_type = 'location'

        if data_type is None or not isinstance(data_type, str):
            raise InvalidEventError("dataType field missing or invalid")

        if data_type == 'location':
            self.process_location_event(event)
        elif data_type == 'sensor2':
            self.process_sensor_event(event)
        elif data_type == 'device_info':
            self.process_device_info_event(event)
        elif data_type == 'heartbeat':
            self.process_heartbeat_event(event)
        else:
            raise InvalidEventError("unknown data type: %s" % data_type)

    def process_events(self):
        events = ReceiveData.objects.filter(imported_at__isnull=True).order_by('received_at')
        for event in events:
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag('event-id', int(event.id))
                scope.set_tag('event-received-at', str(event.received_at))

                with transaction.atomic():
                    try:
                        with transaction.atomic():
                            try:
                                self.process_event(event)
                            except Exception as e:
                                sentry_sdk.capture_exception(e)
                                if isinstance(e, InvalidEventError):
                                    logger.error(e)
                                else:
                                    logger.error(e, exc_info=True)
                                raise
                    except Exception as e:
                        self.mark_imported(event, failed=True)
                    else:
                        self.mark_imported(event, failed=False)

