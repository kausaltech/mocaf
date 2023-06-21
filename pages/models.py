from django.db import models
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.core.fields import RichTextField
from wagtail.core.models import Page
from wagtail_localize.fields import TranslatableField, SynchronizedField


class BlogPost(Page):
    tagline = models.CharField(max_length=255)
    body = RichTextField()
    device_groups = models.ManyToManyField('trips.DeviceGroup', blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('tagline'),
        FieldPanel('body'),
    ]
    settings_panels = Page.settings_panels + [
        FieldPanel('device_groups'),
    ]

    subpage_types = []
    parent_page_types = ['pages.BlogPostIndex']


class InfoPage(Page):
    static_identifier = models.CharField(max_length=20, null=True, blank=True)
    hidden_from_index = models.BooleanField(default=False)
    body = RichTextField()
    device_groups = models.ManyToManyField('trips.DeviceGroup', blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]
    settings_panels = Page.settings_panels + [
        FieldPanel('static_identifier'),
        FieldPanel('hidden_from_index'),
        FieldPanel('device_groups'),
    ]
    translatable_fields = [
        TranslatableField('body'),
        TranslatableField('title'),
        TranslatableField('slug'),
        TranslatableField('seo_title'),
        SynchronizedField('show_in_menus'),
        TranslatableField('search_description'),
        SynchronizedField('static_identifier'),
        SynchronizedField('hidden_from_index'),
        TranslatableField('body'),
    ]

    subpage_types = []
    parent_page_types = ['pages.InfoPageIndex']


class VisualisationGuidePage(Page):
    body = RichTextField()

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    subpage_types = []
    parent_page_types = ['pages.VisualisationGuidePageIndex']


class VisualisationGuidePageIndex(Page):
    max_count = 1
    subpage_types = [VisualisationGuidePage]


class BlogPostIndex(Page):
    max_count = 1
    subpage_types = [BlogPost]


class InfoPageIndex(Page):
    max_count = 1
    subpage_types = [InfoPage]
