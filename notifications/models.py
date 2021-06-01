from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from modeltrans.fields import TranslationField
from wagtail.admin.edit_handlers import FieldPanel


class EventTypeChoices(models.TextChoices):
    MONTHLY_SUMMARY = 'monthly_summary', _("Monthly summary")
    WELCOME_MESSAGE = 'welcome_message', _("Welcome message")
    NO_RECENT_TRIPS = 'no_recent_trips', _("No recent trips")


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
        FieldPanel(f'body_{language}') for language, _ in settings.LANGUAGES
    ]

    def __str__(self):
        return self.title
