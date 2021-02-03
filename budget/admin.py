from django.contrib import admin

from .models import DailyEmissionBudget


class DailyEmissionBudgetAdmin(admin.ModelAdmin):
    list_display = ('year', 'amount')


admin.site.register(DailyEmissionBudget, DailyEmissionBudgetAdmin)
