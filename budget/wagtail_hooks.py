from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register

from .models import EmissionBudgetLevel


@modeladmin_register
class EmissionBudgetLevelAdmin(ModelAdmin):
    model = EmissionBudgetLevel
    menu_icon = 'snippet'
    list_display = ['name', 'year']
