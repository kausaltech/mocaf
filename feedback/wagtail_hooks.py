from wagtail.contrib.modeladmin.helpers import PermissionHelper
from wagtail.contrib.modeladmin.options import ModelAdmin, modeladmin_register
from .models import DeviceFeedback


class DeviceFeedbackPermissionHelper(PermissionHelper):
    def user_can_list(self, user):
        return True

    def user_can_create(self, user):
        return False

    def user_can_inspect_obj(self, user, obj):
        return True

    def user_can_delete_obj(self, user, obj):
        return True

    def user_can_edit_obj(self, user, obj):
        return False


@modeladmin_register
class DeviceFeedbackAdmin(ModelAdmin):
    model = DeviceFeedback
    menu_icon = 'mail'
    permission_helper_class = DeviceFeedbackPermissionHelper
    list_display = ['created_at', 'device_brand', 'comment']
    inspect_view_enabled = True
