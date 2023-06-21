import sys
from functools import partial
from django.apps import AppConfig
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _
from prometheus_client import Gauge


def length_for_mode(mode):
    from trips.models import Leg
    return Leg.objects.filter(mode=mode).aggregate(Sum('length'))['length__sum'] or 0


class TripsConfig(AppConfig):
    name = 'trips'
    verbose_name = _('Trips')

    def ready(self):
        """Set up Prometheus gauges."""
        # Don't do this in management commands other than runserver
        # https://stackoverflow.com/questions/65072296/django-execute-code-only-for-manage-py-runserver-not-for-migrate-help-e
        is_manage_py = any(arg.endswith("manage.py") for arg in sys.argv)
        is_runserver = any(arg == "runserver" for arg in sys.argv)
        is_pytest = 'pytest' in sys.modules
        if not is_pytest and ((is_manage_py and is_runserver) or (not is_manage_py)):
            from trips.models import TransportMode
            gauge = Gauge('trips_length_meters_total', "Total meters by mode of transportation", ['mode'])
            for mode in TransportMode.objects.all():
                gauge.labels(mode.identifier).set_function(partial(length_for_mode, mode))
