from django.contrib import admin

from .models import EmissionBudgetLevel


class EmissionBudgetLevelAdmin(admin.ModelAdmin):
    pass


admin.site.register(EmissionBudgetLevel, EmissionBudgetLevelAdmin)
