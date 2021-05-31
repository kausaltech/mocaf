from django.core.management.base import BaseCommand, CommandError
from transitrt.rt_import import make_importer


class Command(BaseCommand):
    help = 'Updates transit locations from SIRI-RT feed'

    def add_arguments(self, parser):
        parser.add_argument('--url', action='store_true', help='Read locations from URL')
        parser.add_argument(
            '--url-poll-count', type=int, help='How many times to poll the URL',
            default=1,
        )
        parser.add_argument(
            '--url-poll-delay', type=int, help='How many ms to sleep between poll attempts',
            default=5000
        )
        parser.add_argument('importer', type=str)
        parser.add_argument('files', nargs='*', type=str)

    def handle(self, *args, **options):
        rt_importer = make_importer(options['importer'])
        print(options)
        if options['url'] and options['files']:
            raise CommandError("Specify either --url or files, not both")

        if options['url']:
            rt_importer.update_from_url(count=options['url_poll_count'], delay=options['url_poll_delay'])

        if options['files']:
            rt_importer.update_from_files(options['files'])
