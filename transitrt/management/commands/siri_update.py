from django.core.management.base import BaseCommand, CommandError
from transitrt.siri_import import SiriImporter


class Command(BaseCommand):
    help = 'Updates transit locations from SIRI-RT feed'

    def add_arguments(self, parser):
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
        siri_importer = SiriImporter()
        if options['url']:
            siri_importer.update_from_url(options['url'])
        if options['files']:
            siri_importer.update_from_files(options['files'])
