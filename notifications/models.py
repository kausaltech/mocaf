from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from jinja2 import StrictUndefined, Template
from modeltrans.fields import TranslationField
from modeltrans.utils import build_localized_fieldname
from wagtail.admin.edit_handlers import FieldPanel, HelpPanel

from trips.models import Device


class EventTypeChoices(models.TextChoices):
    MONTHLY_SUMMARY = 'monthly_summary', _("Monthly summary")
    WELCOME_MESSAGE = 'welcome_message', _("Welcome message")
    NO_RECENT_TRIPS = 'no_recent_trips', _("No recent trips")


# Make sure the following  variables are set in the relevant context() method of a NotificationTask subclass.
available_variables = {
    EventTypeChoices.MONTHLY_SUMMARY: [
        ('carbon_footprint', _("The user's carbon footprint in kg for the last month")),
        ('average_carbon_footprint', _("Average carbon footprint of active devices for the last month")),
    ],
    EventTypeChoices.WELCOME_MESSAGE: [],
    EventTypeChoices.NO_RECENT_TRIPS: [],
}

variable_help_text = '<ul>'
for event_type, variables in available_variables.items():
    if variables:
        variable_help_text += f'<li style="list-style-type: disc">{event_type.label}:<ul>'
        for name, description in variables:
            li_style = 'list-style-type: circle; margin-left: 2em'
            variable_help_text += f'<li style="{li_style}"><b>{name}</b>: {description}</li>'
        variable_help_text += '</ul></li>'
variable_help_text += '</ul>'


class BodyPanel(FieldPanel):
    def on_form_bound(self):
        super().on_form_bound()
        self.help_text = _("Notification body; variables can be substituted using the syntax {{ x }}.")


class NotificationTemplate(models.Model):
    event_type = models.CharField(max_length=20, choices=EventTypeChoices.choices)
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
        template = Template(field, undefined=StrictUndefined)
        return template.render(**kwargs)

    def render_all_languages(self, field_name, **kwargs):
        """Return dict mapping each of the languages the notification API expects to a rendering of the given fields in
        the respective language.

        kwargs are passed as context when rendering the template.
        """
        return {language: self.render(field_name, language, **kwargs) for language in ('fi', 'en')}


class NotificationLogEntry(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    template = models.ForeignKey(NotificationTemplate, on_delete=models.SET_NULL, null=True)
    sent_at = models.DateTimeField()
