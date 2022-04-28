from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import gettext_lazy as _, override
from jinja2 import StrictUndefined, Template
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
                       EventTypeChoices.MONTHLY_SUMMARY_BRONZE_OR_WORSE)
    },
    EventTypeChoices.WELCOME_MESSAGE: [],
    EventTypeChoices.NO_RECENT_TRIPS: [],
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
    body = models.TextField()

    i18n = TranslationField(fields=('title', 'body',))

    panels = [
        FieldPanel('event_type'),
        HelpPanel(heading=_("Available variables by event type"), content=variable_help_text),
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


class NotificationLogEntry(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True)
    sent_at = models.DateTimeField()
