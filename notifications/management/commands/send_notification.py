import datetime
from django.core.management.base import BaseCommand
from django.utils.timezone import utc

from trips.models import Device
from notifications.engine import NotificationEngine
from notifications.tasks import MonthlySummaryNotificationTask, registered_tasks, send_notifications


class Command(BaseCommand):
    help = "Send a notification of a given type to a given device"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_classes = {c.__name__: c for c in registered_tasks}

    def add_arguments(self, parser):
        parser.add_argument('task_class',
                            choices=self.task_classes.keys(),
                            help="Class of the task to be executed")
        parser.add_argument('--api-url', nargs='?')
        parser.add_argument('--api-token', nargs='?')
        parser.add_argument('--date',
                            type=datetime.date.fromisoformat,
                            help="Date (ISO format) to use instead of the current one")
        parser.add_argument('--dry-run', action='store_true', help="Do not send notifications but print them instead")
        parser.add_argument('--force',
                            action='store_true',
                            help="Send notifications to devices regardless of whether devices qualify for the "
                            "notification")
        parser.add_argument('--min-active-days',
                            type=int,
                            default=0,
                            help="Minimum number of active days in the last month in order to receive a prize")
        parser.add_argument('--restrict-average',
                            action='store_true',
                            help="Use potential recipients' footprint as average to avoid expensive recomputation for "
                            "all devices (only for monthly summary notifications)")

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--device', action='append', help="Send notification to device with given UUID", default=[])
        group.add_argument('--all-devices', action='store_true', help="Send notifications to all devices")

    def handle(self, *args, **options):
        task_class = self.task_classes[options['task_class']]
        self.send_notification(task_class,
                               options.get('device'),
                               options.get('all_devices'),
                               api_url=options.get('api_url'),
                               api_token=options.get('api_token'),
                               date=options.get('date'),
                               dry_run=options.get('dry_run'),
                               force=options.get('force'),
                               restrict_average=options.get('restrict_average'),
                               min_active_days=options.get('min_active_days'))

    def send_notification(
        self, task_class, uuids, all_devices=False, api_url=None, api_token=None, date=None, dry_run=False, force=False,
        restrict_average=False, min_active_days=0
    ):
        for uuid in uuids:
            if not Device.objects.filter(uuid=uuid).exists():
                raise ValueError(f"Device {uuid} does not exist")

        if all_devices:
            devices = None
        else:
            devices = Device.objects.filter(uuid__in=uuids)

        if date:
            now = datetime.datetime.combine(date, datetime.time(), utc)
        else:
            now = None

        engine = NotificationEngine(api_url, api_token)
        kwargs = {
            'engine': engine,
            'dry_run': dry_run,
            'now': now,
            'force': force,
            'min_active_days': min_active_days,
        }
        if issubclass(task_class, MonthlySummaryNotificationTask):
            kwargs['restrict_average'] = restrict_average
        send_notifications(task_class, devices, **kwargs)
