from wagtail.contrib.modeladmin.helpers import PermissionHelper
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from .models import DeviceFeedback


class DeviceFeedbackPermissionHelper(PermissionHelper):
    def user_can_create(self, user):
        return False


@modeladmin_register
class DeviceFeedbackAdmin(ModelAdmin):
    model = DeviceFeedback
    # menu_icon = 'help'
    permission_helper_class = DeviceFeedbackPermissionHelper
    list_display = ['created_at', 'device_brand', 'comment']
