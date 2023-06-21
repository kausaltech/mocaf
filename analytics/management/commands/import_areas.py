from django.core.management.base import BaseCommand
from analytics.areas.tampere import TampereImporter, TamperePaavoImporter
from analytics.areas.paavo import PaavoImporter
from analytics.areas.tampere_poi import TamperePOIImporter


area_importers = [
    TampereImporter(),
    TamperePaavoImporter(),
    PaavoImporter(),
    TamperePOIImporter(),
]


class Command(BaseCommand):
    help = 'Import analytics areas'

    def add_arguments(self, parser):
        parser.add_argument('types', nargs='*', type=str)
        parser.add_argument('--all', action='store_true')
        parser.add_argument('--list', action='store_true')
        parser.add_argument('--geojson', action='store_true')

    def print_types(self):
        print('Supported types:')
        for ai in area_importers:
            ats = ai.get_area_types()
            for id, conf in ats.items():
                print('\t%-20s %s' % (id, conf['name']))

    def handle(self, *args, **options):
        if options['list'] or (not options['types'] and not options['all']):
            self.print_types()
            return

        if options['all'] and options['types']:
            print("Enumerate the types or supply '--all', not both")
            self.print_types()
            exit(1)

        types = set(options['types'])
        for ai in area_importers:
            ats = ai.get_area_types()
            for t in ats:
                if not options['all'] and t not in types:
                    continue
                print('Importing %s' % t)
                ai.import_area_type(t)
                if not options['all']:
                    types.remove(t)

        if types:
            print('Unknown area types: %s' % ', '.join(types))
            self.print_types()
            exit(1)
