from django.db import models
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page


class BlogPost(Page):
    lead_paragraph = models.CharField(max_length=255, blank=True)
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('lead_paragraph'),
        FieldPanel('body'),
    ]

    subpage_types = []
