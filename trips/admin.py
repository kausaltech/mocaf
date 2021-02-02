from django.contrib import admin
from .models import TransportMode


class TransportModeAdmin(admin.ModelAdmin):
    pass


admin.site.register(TransportMode, TransportModeAdmin)
