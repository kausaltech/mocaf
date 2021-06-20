from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from wagtail.contrib.modeladmin.views import InspectView
from .models import NotificationTemplate


@modeladmin_register
class NotificationTemplateAdmin(ModelAdmin):
    model = NotificationTemplate
    menu_icon = 'edit'
    inspect_view_enabled = True
    inspect_view_fields = [
        f'title_{lang}_preview' for lang in ('fi', 'en', 'sv')
    ] + [
        f'body_{lang}_preview' for lang in ('fi', 'en', 'sv')
    ]
