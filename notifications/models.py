from django.conf import settings
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _, override
from jinja2 import StrictUndefined, Template
from jinja2.exceptions import UndefinedError
from modeltrans.fields import TranslationField
from modeltrans.utils import build_localized_fieldname
from wagtail.admin.edit_handlers import FieldPanel, HelpPanel

from trips.models import Device


class EventTypeChoices(models.TextChoices):
    MONTHLY_SUMMARY_GOLD = 'monthly_summary_gold', _("Monthly summary (gold-level budget)")
    MONTHLY_SUMMARY_SILVER = 'monthly_summary_silver', _("Monthly summary (silver-level budget)")
    MONTHLY_SUMMARY_BRONZE_OR_WORSE = 'monthly_summary_geq_bronze', _("Monthly summary (bronze-level budget or worse)")
    MONTHLY_SUMMARY_BRONZE = 'monthly_summary_bronze', _("Monthly summary (bronze-level budget)")
    MONTHLY_SUMMARY_NO_LEVEL_REACHED = 'monthly_summary_no_level', _("Monthly summary (worse than bronze budget)")
    WELCOME_MESSAGE = 'welcome_message', _("Welcome message")
    NO_RECENT_TRIPS = 'no_recent_trips', _("No recent trips")
    HEALTH_SUMMARY_GOLD = 'health_summary_gold', _("Health summary (gold-level budget)")
    HEALTH_SUMMARY_SILVER = 'health_summary_silver', _("Health summary (silver-level budget)")
    HEALTH_SUMMARY_BRONZE = 'health_summary_bronze', _("Health summary (bronze-level budget)")
    HEALTH_SUMMARY_NO_LEVEL_REACHED = 'health_summary_no_level', _("Health summary (worse than bronze budget)")
    HEALTH_SUMMARY_NO_DATA = 'health_summary_no_data', _("Health summary (no physical activity trips)")
    TIMED_MESSAGE = 'timed_message', _("Timed message")


def example_month(language):
    with override(language):
        today = timezone.now().date()
        return date_format(today, 'F')


# Make sure the following  variables are set in the relevant context() method of a NotificationTask subclass.
# List elements: (variable_name, description, example_value)
# TODO: Create a class for this.
available_variables = {
    **{
        choice: [
            ('average_carbon_footprint', _("Average carbon footprint in kg of active devices for the last month"),
             123.45),
            ('carbon_footprint', _("The user's carbon footprint in kg for the last month"), 123.45),
            ('month', _("Month that is being summarized in the notification"), example_month),
        ]
        for choice in (EventTypeChoices.MONTHLY_SUMMARY_GOLD,
                       EventTypeChoices.MONTHLY_SUMMARY_SILVER,
                       EventTypeChoices.MONTHLY_SUMMARY_BRONZE_OR_WORSE,
                       EventTypeChoices.MONTHLY_SUMMARY_BRONZE,
                       EventTypeChoices.MONTHLY_SUMMARY_NO_LEVEL_REACHED,)
    },
    **{
        choice: [
            ('bicycle_walk_mins', _("Biking and walking trip minutes"), 123.45),
            ('bicycle_mins', _("Biking trip minutes"), 123.45),
            ('walk_mins', _("Walking trip minutes"), 123.45),
            ('average_bicycle_walk_mins', _("Average biking and walking trip minutes (for all active devices)"), 123.45),
            ('average_bicycle_mins', _("Average biking trip minutes (for all active devices)"), 123.45),
            ('average_walk_mins', _("Average walking trip minutes (for all active devices)"), 123.45),
        ]
        for choice in (EventTypeChoices.HEALTH_SUMMARY_GOLD,
                       EventTypeChoices.HEALTH_SUMMARY_SILVER,
                       EventTypeChoices.HEALTH_SUMMARY_BRONZE,
                       EventTypeChoices.HEALTH_SUMMARY_NO_DATA,
                       EventTypeChoices.HEALTH_SUMMARY_NO_LEVEL_REACHED)
    },
    EventTypeChoices.WELCOME_MESSAGE: [],
    EventTypeChoices.NO_RECENT_TRIPS: [],
    EventTypeChoices.TIMED_MESSAGE: [],
}

variable_help_text = '<ul style="margin-left: 1em">'
for event_type, variables in available_variables.items():
    if variables:
        variable_help_text += f'<li style="list-style-type: disc">{event_type.label}:<ul>'
        for name, description, example_value in variables:
            li_style = 'list-style-type: circle; margin-left: 2em'
            variable_help_text += f'<li style="{li_style}"><b>{name}</b>: {description}</li>'
        variable_help_text += '</ul></li>'
variable_help_text += '</ul>'
instructions = _("You can see a preview of the notification be clicking <i>inspect</i> in the template list.")
variable_help_text += f'<p style="margin-top: 1ex">{instructions}</p>'


class BodyPanel(FieldPanel):
    def on_form_bound(self):
        super().on_form_bound()
        self.help_text = _("Notification body; variables can be substituted using the syntax {{ x }}.")


class NotificationTemplate(models.Model):
    event_type = models.CharField(max_length=26, choices=EventTypeChoices.choices)
    title = models.CharField(max_length=255)
    send_on = models.DateField(blank=True, null=True, help_text="Date on which the timed notification will be sent")
    groups = models.ManyToManyField('trips.DeviceGroup', blank=True)
    body = models.TextField()

    i18n = TranslationField(fields=('title', 'body',))

    panels = [
        FieldPanel('event_type'),
        HelpPanel(heading=_("Available variables by event type"), content=variable_help_text),
        FieldPanel('send_on'),
        FieldPanel('groups'),
    ] + [
        FieldPanel(f'title_{language}') for language, _ in settings.LANGUAGES
    ] + [
        BodyPanel(f'body_{language}') for language, _ in settings.LANGUAGES
    ]

    def __str__(self):
        return self.title

    def render(self, field_name, language=None, **kwargs):
        """Render the given field as a Jinja2 template.

        If language is not specified, the active language is used (using the the default language as a fallback).
        kwargs are passed as context when rendering the template.
        """
        if language is None:
            language = 'i18n'
        field = getattr(self, build_localized_fieldname(field_name, language))
        if field is None:  # can happen if the field has no value for that language
            field = ''
        template = Template(field, undefined=StrictUndefined)
        return template.render(**kwargs)

    def render_all_languages(self, field_name, contexts):
        """Return dict mapping each of the languages the notification API expects to a rendering of the given fields in
        the respective language.

        `contexts` is a dict mapping each available language to a template context
        """
        return {language: self.render(field_name, language, **contexts[language]) for language in ('fi', 'en')}

    def render_preview(self, field_name, language=None):
        context = {}
        for name, d, value in available_variables[self.event_type]:
            if callable(value):
                context[name] = value(language=language)
            else:
                context[name] = value
        return self.render(field_name, language, **context)

    def title_preview(self, language=None):
        return self.render_preview('title', language)

    def body_preview(self, language=None):
        return self.render_preview('body', language)

    # TODO: Dynamically create the following methods
    def title_fi_preview(self):
        return self.title_preview('fi')

    def title_en_preview(self):
        return self.title_preview('en')

    def title_sv_preview(self):
        return self.title_preview('sv')

    def body_fi_preview(self):
        return self.body_preview('fi')

    def body_en_preview(self):
        return self.body_preview('en')

    def body_sv_preview(self):
        return self.body_preview('sv')

    def groups_text(self) -> str:
        return ', '.join([grp.name for grp in self.groups.all()])
    groups_text.short_description = 'Groups'

    def clean(self):
        super().clean()
        errors = {}
        for lang in ('fi', 'en'):
            for field in ('body', 'title'):
                try:
                    self.render_preview(field, lang)
                except UndefinedError as e:
                    errors['%s_%s' % (field, lang)] = e.message
        if errors:
            raise ValidationError(errors)


class NotificationLogEntry(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True)
    sent_at = models.DateTimeField()
