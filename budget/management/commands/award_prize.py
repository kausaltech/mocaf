from django.core.management.base import BaseCommand

from trips.models import Device
from budget.models import EmissionBudgetLevel
from budget.prize_api import PrizeApi
from budget.tasks import award_prizes


class Command(BaseCommand):
    help = "Award a prize of a given type to a given device"

    def add_arguments(self, parser):
        self.next_higher_budget_level = {
            'bronze': 'silver',
            'silver': 'gold',
            'gold': None,
        }
        budget_level_choices = self.next_higher_budget_level.keys()

        parser.add_argument('budget_level', choices=budget_level_choices, help="Prize level to be awarded")
        parser.add_argument('--api-url', nargs='?')
        parser.add_argument('--api-token', nargs='?')
        parser.add_argument('--dry-run', action='store_true', help="Do not award prizes but print them instead")
        parser.add_argument('--force',
                            action='store_true',
                            help="Award prize to device regardless of whether the device qualifies for the prize")

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--device', action='append', help="Award prize to device with given UUID", default=[])
        group.add_argument('--all-devices', action='store_true', help="Award prizes to all devices")

    def handle(self, *args, **options):
        self.award_prize(options['budget_level'],
                         options['device'],
                         next_budget_level_identifier=self.next_higher_budget_level[options['budget_level']],
                         all_devices=options['all_devices'],
                         api_url=options.get('api_url'),
                         api_token=options.get('api_token'),
                         dry_run=options.get('dry_run'),
                         force=options.get('force'))

    def award_prize(
        self, budget_level_identifier, uuids, next_budget_level_identifier=None, all_devices=False, api_url=None,
        api_token=None, dry_run=False, force=False
    ):
        for uuid in uuids:
            if not Device.objects.filter(uuid=uuid).exists():
                raise ValueError(f"Device {uuid} does not exist")

        if all_devices:
            devices = Device.objects.all()
        else:
            devices = Device.objects.filter(uuid__in=uuids)

        prize_api = PrizeApi(api_url, api_token)
        award_prizes(
            budget_level_identifier,
            next_budget_level_identifier=next_budget_level_identifier,
            devices=devices,
            prize_api=prize_api,
            dry_run=dry_run,
            force=force,
        )
