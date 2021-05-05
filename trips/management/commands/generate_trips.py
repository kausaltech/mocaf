from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from trips.models import Device
from trips.generate import TripGenerator
from calc.trips import read_uuids


class Command(BaseCommand):
    help = 'Generate trips based on location samples'

    def add_arguments(self, parser):
        parser.add_argument('--uuid', type=str)
        parser.add_argument('--start-after-uuid', type=str)
        parser.add_argument('--new', action='store_true')

    def handle(self, *args, **options):
        generator = TripGenerator()
        uuid = options['uuid']
        start_uuid = options['start_after_uuid']
        #start_time = datetime(2021, 4, 28, 0)
        #end_time = start_time + timedelta(days=1)
        start_time = None
        end_time = None

        generator.begin()
        if options['new']:
            generator.generate_new_trips()
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
