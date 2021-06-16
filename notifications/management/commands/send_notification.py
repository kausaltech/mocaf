from django.core.management.base import BaseCommand

from trips.models import Device
from notifications.engine import NotificationEngine
from notifications.tasks import NotificationTask, send_notifications


class Command(BaseCommand):
    help = "Send a notification of a given type to a given device"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_classes = {c.__name__: c for c in NotificationTask.__subclasses__()}

    def add_arguments(self, parser):
        parser.add_argument('device', help="UUID of recipient device")
        parser.add_argument('task_class',
                            choices=self.task_classes.keys(),
                            help="Class of the task to be executed")
        parser.add_argument('--api-url', nargs='?')
        parser.add_argument('--api-token', nargs='?')

    def handle(self, *args, **options):
        task_class = self.task_classes[options['task_class']]
        self.send_notification(options['device'],
                               task_class,
                               api_url=options.get('api_url'),
                               api_token=options.get('api_token'))

    def send_notification(self, uuid, task_class, api_url=None, api_token=None):
        devices = [Device.objects.get(uuid=uuid)]
        engine = NotificationEngine(api_url, api_token)
        send_notifications(task_class=task_class, devices=devices, engine=engine)
