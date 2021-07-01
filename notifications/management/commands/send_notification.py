from django.core.management.base import BaseCommand

from trips.models import Device
from notifications.engine import NotificationEngine
from notifications.tasks import MonthlySummaryNotificationTask, registered_tasks, send_notifications


class Command(BaseCommand):
    help = "Send a notification of a given type to a given device"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_classes = {c.__name__: c for c in registered_tasks}

    def add_arguments(self, parser):
        parser.add_argument('device', help="UUID of recipient device")
        parser.add_argument('task_class',
                            choices=self.task_classes.keys(),
                            help="Class of the task to be executed")
        parser.add_argument('--api-url', nargs='?')
        parser.add_argument('--api-token', nargs='?')
        parser.add_argument('--dry-run', action='store_true', help="Do not send notifications but print them instead")
        parser.add_argument('--force-recipient',
                            action='store_true',
                            help="Send notification to device regardless of whether it qualifies for the notification")
        parser.add_argument('--restrict-average',
                            action='store_true',
                            help="Use device's footprint as average to avoid expensive recomputation for all devices "
                            "(only for monthly summary notifications)")

    def handle(self, *args, **options):
        task_class = self.task_classes[options['task_class']]
        self.send_notification(options['device'],
                               task_class,
                               api_url=options.get('api_url'),
                               api_token=options.get('api_token'),
                               dry_run=options.get('dry_run'),
                               force_recipients=options.get('force_recipient'),
                               restrict_average=options.get('restrict_average'))

    def send_notification(
        self, uuid, task_class, api_url=None, api_token=None, dry_run=False, force_recipients=False,
        restrict_average=False
    ):
        devices = Device.objects.filter(uuid=uuid)
        engine = NotificationEngine(api_url, api_token)
        kwargs = {
            'engine': engine,
            'dry_run': dry_run,
            'force_recipients': force_recipients,
        }
        if issubclass(task_class, MonthlySummaryNotificationTask):
            kwargs['restrict_average'] = restrict_average
        send_notifications(task_class, devices, **kwargs)
