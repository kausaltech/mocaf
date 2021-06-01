from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from jinja2 import StrictUndefined, Template
from modeltrans.fields import TranslationField
from wagtail.admin.edit_handlers import FieldPanel


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

    def render_body(self, **kwargs):
        """Render the body in the active language as a Jinja2 template.

        kwargs are passed as context when rendering the template.
        """
        template = Template(self.body_i18n, undefined=StrictUndefined)
        return template.render(**kwargs)
