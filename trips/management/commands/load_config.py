import yaml
from django.core.management.base import BaseCommand, CommandError
from trips.models import TransportMode
from budget.models import EmissionBudgetLevel


class Command(BaseCommand):
    help = 'Load global config from file'

    def add_arguments(self, parser):
        parser.add_argument('file', type=str)

    def update_emission_budget_levels(self, data):
        levels = {}
        for level in EmissionBudgetLevel.objects.all():
            years = levels.setdefault(level.identifier, {})
            years[level.year] = level

        print('Updating emission budget levels')
        for item in data:
            years = levels.get(item['identifier'], {})
            level = years.get(int(item['year']))
            if level is None:
                level = EmissionBudgetLevel(identifier=item['identifier'], year=item['year'])
            level.name = item['name']
            if 'name_en' in item:
                level.name_en = item['name_en']
            level.carbon_footprint = item['carbon_footprint']
            level.save()
            print('Saved %s' % level)

    def update_transport_modes(self, data):
        print('Updating transport modes')
        modes = {x.identifier: x for x in TransportMode.objects.all()}
        for item in data:
            mode = modes.get(item['identifier'])
            if mode is None:
                mode = TransportMode(identifier=item['identifier'])
            mode.name = item['name']
            if 'name_en' in item:
                mode.name_en = item['name_en']
            mode.emission_factor = item['emission_factor']
            mode.save()
            print('Saved: %s' % mode)

    def handle(self, *args, **options):
        fn = options['file']
        with open(fn, 'r') as f:
            data = yaml.safe_load(f)
        self.update_emission_budget_levels(data['emission_budget_levels'])
        self.update_transport_modes(data['transport_modes'])
