from django.contrib import admin
from .models import TransportMode


class TransportModeAdmin(admin.ModelAdmin):
    list_display = ('name', 'emission_factor')


admin.site.register(TransportMode, TransportModeAdmin)
