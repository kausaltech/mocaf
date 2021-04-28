import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mocaf.settings')

app = Celery('mocaf')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    print('add periodic task')
    sender.add_periodic_task(5, debug_task, expires=4)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
