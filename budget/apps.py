from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BudgetConfig(AppConfig):
    name = 'budget'
    verbose_name = _('Emission budget')
