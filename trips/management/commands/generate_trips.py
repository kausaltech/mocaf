from django.core.management.base import BaseCommand, CommandError
from dateutil.parser import parse
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils.timezone import localdate
from trips.models import Device, LOCAL_TZ
from trips.generate import TripGenerator
from calc.trips import read_uuids


class Command(BaseCommand):
    help = 'Generate trips based on location samples'

    def add_arguments(self, parser):
        parser.add_argument('--uuid', type=str)
        parser.add_argument('--start-after-uuid', type=str)
        parser.add_argument('--new', action='store_true')
        parser.add_argument('--start-time', type=str)
        parser.add_argument('--end-time', type=str)
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        generator = TripGenerator(force=options['force'])
        uuid = options['uuid']
        start_uuid = options['start_after_uuid']
        start_time = options['start_time']
        end_time = options['end_time']
        if start_time:
            start_time = parse(start_time)
            if not start_time.tzinfo:
                start_time = LOCAL_TZ.localize(start_time)
        if end_time:
            end_time = parse(end_time)
            if not end_time.tzinfo:
                end_time = LOCAL_TZ.localize(end_time)

        generator.begin()
        if options['new']:
            generator.generate_new_trips(only_uuid=options['uuid'])
        else:
            if uuid:
                uuids = [uuid]
            else:
                uuids = read_uuids(connection)

            for uuid in uuids:
                if start_uuid:
                    if uuid == start_uuid:
                        start_uuid = None
                    continue
                device = Device.objects.filter(uuid=uuid).first()
                if device is None:
                    print('Device %s not found' % device)
                    continue
                generator.generate_trips(uuid, start_time, end_time)

        generator.end()
