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
        from trips.models import TransportMode
        gauge = Gauge('trips_length_meters_total', "Total meters by mode of transportation", ['mode'])
        for mode in TransportMode.objects.all():
            gauge.labels(mode.identifier).set_function(partial(length_for_mode, mode))
