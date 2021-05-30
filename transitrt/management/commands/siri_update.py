from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from gtfs.models import Agency
from transitrt.siri_import import SiriImporter


class Command(BaseCommand):
    help = 'Updates transit locations from SIRI-RT feed'

    def add_arguments(self, parser):
        parser.add_argument('--agency', type=str, help='GTFS agency name')
        parser.add_argument('--url', type=str, help='Read locations from URL')
        parser.add_argument(
            '--url-poll-count', type=int, help='How many times to poll the URL',
            default=1,
        )
        parser.add_argument(
            '--url-poll-delay', type=int, help='How many ms to sleep between poll attempts',
            default=5000
        )
        parser.add_argument('files', nargs='*', type=str)

    def handle(self, *args, **options):
        agencies = Agency.objects.all()
        if options['agency']:
            agencies = agencies.filter(
                Q(agency__agency_id__iexact=options['agency']) | Q(agency__agency_name__iexact=options['agency'])
            )
        if len(agencies) != 1:
            raise CommandError("Specify agency name with --agency")

        siri_importer = SiriImporter(agency_id=agencies.first().id)
        if options['url']:
            siri_importer.update_from_url(options['url'])
        if options['files']:
            siri_importer.update_from_files(options['files'])
