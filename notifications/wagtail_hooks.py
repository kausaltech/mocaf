from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from .models import NotificationTemplate


@modeladmin_register
class NotificationTemplateAdmin(ModelAdmin):
    model = NotificationTemplate
    menu_icon = 'edit'
