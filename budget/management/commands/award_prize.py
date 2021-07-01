from django.core.management.base import BaseCommand

from trips.models import Device
from budget.models import EmissionBudgetLevel
from budget.prize_api import PrizeApi
from budget.tasks import award_prizes


class Command(BaseCommand):
    help = "Award a prize of a given type to a given device"

    def add_arguments(self, parser):
        available_budget_levels = EmissionBudgetLevel.objects.values_list('identifier', flat=True)

        parser.add_argument('device', help="UUID of recipient device")
        parser.add_argument('budget_level', choices=available_budget_levels, help="Prize level to be awarded")
        parser.add_argument('--api-url', nargs='?')
        parser.add_argument('--api-token', nargs='?')
        parser.add_argument('--dry-run', action='store_true', help="Do not award prizes but print them instead")
        parser.add_argument('--force',
                            action='store_true',
                            help="Award prize to device regardless of whether the device qualifies for the prize")

    def handle(self, *args, **options):
        self.award_prize(options['device'],
                         options['budget_level'],
                         api_url=options.get('api_url'),
                         api_token=options.get('api_token'),
                         dry_run=options.get('dry_run'),
                         force=options.get('force'))

    def award_prize(self, uuid, budget_level_identifier, api_url=None, api_token=None, dry_run=False, force=False):
        devices = Device.objects.filter(uuid=uuid)
        prize_api = PrizeApi(api_url, api_token)
        award_prizes(budget_level_identifier, devices=devices, prize_api=prize_api, dry_run=dry_run, force=force)
