from django.db import models
from django.utils.translation import gettext_lazy as _


class DailyEmissionBudget(models.Model):
    year = models.PositiveIntegerField(verbose_name=_('Year'))
    amount = models.FloatField(
        verbose_name=_('Emission amount'),
        help_text=_('Amount of mobility carbon emissions per resident per day (in grams of CO2e.)')
    )

    class Meta:
        verbose_name = _('Daily emission budget')
        verbose_name_plural = _('Daily emission budgets')
