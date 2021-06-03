from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from jinja2 import StrictUndefined, Template
from modeltrans.fields import TranslationField
from modeltrans.utils import build_localized_fieldname
from wagtail.admin.edit_handlers import FieldPanel

from trips.models import Device


class EventTypeChoices(models.TextChoices):
    MONTHLY_SUMMARY = 'monthly_summary', _("Monthly summary")
    WELCOME_MESSAGE = 'welcome_message', _("Welcome message")
    NO_RECENT_TRIPS = 'no_recent_trips', _("No recent trips")


class BodyPanel(FieldPanel):
    def on_form_bound(self):
        super().on_form_bound()
        self.help_text = _("Notification body; variables like x can be substituted using the syntax {{ x }}")


class NotificationTemplate(models.Model):
    event_type = models.CharField(max_length=20, choices=EventTypeChoices.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()

    i18n = TranslationField(fields=('title', 'body',))

    panels = [
        FieldPanel('event_type'),
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

        kwargs are passed as context when rendering the template."""
        return {language: self.render(field_name, language, **kwargs) for language in ('fi', 'en')}
