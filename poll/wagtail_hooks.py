import csv
from django.http import HttpResponse
from django.utils.encoding import smart_str
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.conf.urls import url
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from wagtail.contrib.modeladmin.views import IndexView
from wagtail.contrib.modeladmin.options import (
    ModelAdmin, modeladmin_register, ModelAdminGroup)
from wagtail.contrib.modeladmin.helpers import AdminURLHelper, ButtonHelper
from djqscsv import render_to_csv_response

from .models import Lottery, Trips, Legs, SurveyInfo, Partisipants


class ExportButtonHelper(ButtonHelper):
    export_button_classnames = ['icon', 'icon-download']

    def export_button(self, classnames_add=None, classnames_exclude=None):
        if classnames_add is None:
            classnames_add = []
        if classnames_exclude is None:
            classnames_exclude = []

        classnames = self.export_button_classnames + classnames_add
        cn = self.finalise_classname(classnames, classnames_exclude)
        text = _('Export {} to CSV'.format(self.verbose_name_plural.title()))

        return {
            'url': self.url_helper.get_action_url('export',
                                            query_params=self.request.GET),
            'label': text,
            'classname': cn,
            'title': text,
        }

class ExportAdminURLHelper(AdminURLHelper):
    non_object_specific_actions = ('create', 'choose_parent', 'index', 'export')

    def get_action_url(self, action, *args, **kwargs):
        query_params = kwargs.pop('query_params', None)

        url_name = self.get_action_url_name(action)
        if action in self.non_object_specific_actions:
            url = reverse(url_name)
        else:
            url = reverse(url_name, args=args, kwargs=kwargs)

        if query_params:
            url += '?{params}'.format(params=query_params.urlencode())

        return url

    def get_action_url_pattern(self, action):
        if action in self.non_object_specific_actions:
            return self._get_action_url_pattern(action)

        return self._get_object_specific_action_url_pattern(action)
    
class ExportView(IndexView):
    model_admin = None

    def export_csv(self):
        data = self.queryset.all().values()
        if (self.model_admin is None) or not hasattr(self.model_admin, 'csv_export_fields'):
           data = self.queryset.all().values()
        else:
            data = self.queryset.all().values(*self.model_admin.csv_export_fields)


        return render_to_csv_response(data)


    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        super().dispatch(request, *args, **kwargs)
        return self.export_csv()
    
class ExportModelAdminMixin(object):
    button_helper_class = ExportButtonHelper
    url_helper_class = ExportAdminURLHelper
    export_view_class = ExportView

    def get_admin_urls_for_registration(self):
        urls = super().get_admin_urls_for_registration()
        urls += (url(self.url_helper.get_action_url_pattern('export'),
                        self.export_view,
                        name=self.url_helper.get_action_url_name('export')), )

        return urls

    def export_view(self, request):
        kwargs = {'model_admin': self}
        view_class = self.export_view_class
        return view_class.as_view(**kwargs)(request)


class LotteryAdmin(ExportModelAdminMixin, ModelAdmin):
    model = Lottery
    menu_icon = 'snippet'
    list_display = ['user_name', 'user_email']
    csv_export_fields = ['user_name', 'user_email']
    index_template_name = 'export_csv.html'

class TripAdmin(ExportModelAdminMixin, ModelAdmin):
    model = Trips
    menu_label = "Trips"
    menu_icon = 'snippet'
    list_display = ['start_time', 'end_time', 'start_municipality', 'end_municipality', 'original_trip', 'deleted', 'partisipant', 'purpose']
    index_template_name = 'export_csv.html'

class LegAdmin(ExportModelAdminMixin, ModelAdmin):
    model = Legs
    menu_label = "Legs"
    menu_icon = 'snippet'
    list_display = ['trip', 'start_time', 'end_time', 'trip_length', 'original_leg', 'deleted']
    search_fields = ('trip__id', 'start_time', 'end_time',)
    index_template_name = 'export_csv.html'

class SurveyInfoAdmin(ExportModelAdminMixin, ModelAdmin):
    model = SurveyInfo
    menu_icon = 'snippet'
    list_display = ['start_day', 'end_day', 'days', 'max_back_question', 'description']
    index_template_name = 'export_csv.html'
    search_fields = ('description',)
    

class PartisipantsAdmin(ExportModelAdminMixin, ModelAdmin):
    model = Partisipants
    menu_label = "Partisipants"
    
    menu_icon = 'snippet'
    list_display = ['survey_info', 'start_date', 'end_date', 'approved', 'back_question_answers', 'feeling_question_answers']
    index_template_name = 'export_csv.html'
    search_fields = ('survey_info__description',)
    
@modeladmin_register
class PollGroup(ModelAdminGroup):
    menu_label = "Poll"
    
    menu_icon = 'snippet'
    items = (PartisipantsAdmin, SurveyInfoAdmin, LegAdmin, TripAdmin, LotteryAdmin)
