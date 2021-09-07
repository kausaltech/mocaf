from django.core.management.base import BaseCommand
from analytics.tampere_import import import_areas


class Command(BaseCommand):
    help = 'Import analytics areas'

    def handle(self, *args, **options):
        import_areas()
