from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TripsConfig(AppConfig):
    name = 'trips'
    verbose_name = _('Trips')
