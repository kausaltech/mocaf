from django.core.management.base import BaseCommand

from trips.models import Device
from notifications.engine import NotificationEngine
from notifications.tasks import NotificationTask, registered_tasks, send_notifications


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
        parser.add_argument('--dry-run', action='store_true',
                            help="Neither send notifications nor award prizes but print them instead")

    def handle(self, *args, **options):
        task_class = self.task_classes[options['task_class']]
        self.send_notification(options['device'],
                               task_class,
                               api_url=options.get('api_url'),
                               api_token=options.get('api_token'),
                               dry_run=options.get('dry_run'))

    def send_notification(self, uuid, task_class, api_url=None, api_token=None, dry_run=False):
        devices = [Device.objects.get(uuid=uuid)]
        engine = NotificationEngine(api_url, api_token)
        send_notifications(task_class, devices, engine=engine, dry_run=dry_run)
