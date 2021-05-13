from django.db import models
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page


class BlogPost(Page):
    tagline = models.CharField(max_length=255)
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('tagline'),
        FieldPanel('body'),
    ]

    subpage_types = []


class InfoPage(Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    subpage_types = []
