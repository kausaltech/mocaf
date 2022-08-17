from typing import Optional, TypeVar
from django.db.models import QuerySet, Q

import graphene
from graphene_django import DjangoObjectType
from wagtail.core.models import Page
from wagtail.core.rich_text import expand_db_html

from trips.models import Device

from . import models


class BlogPost(DjangoObjectType):
    class Meta:
        model = models.BlogPost
        fields = ['id', 'title', 'tagline', 'body', 'first_published_at']

    body = graphene.String()
    language = graphene.String()

    def resolve_body(root, info):
        return expand_db_html(root.body)

    def resolve_language(root, info):
        return root.locale.language_code


class InfoPage(DjangoObjectType):
    class Meta:
        model = models.InfoPage
        fields = ['id', 'title', 'body']

    body = graphene.String()

    def resolve_body(root, info):
        return expand_db_html(root.body)


PageModel = TypeVar('PageModel', bound=Page)


def pages_for_device(base_qs: QuerySet[PageModel], device: Optional[Device]) -> QuerySet[PageModel]:
    qs = base_qs.live().public().specific()
    if device is None:
        qs = qs.filter(device_groups__isnull=True)
    else:
        q = Q(device_groups__isnull=True) | Q(device_groups__in=device.groups.all())
        qs = qs.filter(q)
    return qs


class Query(graphene.ObjectType):
    blog_post = graphene.Field(BlogPost, id=graphene.ID(required=True))
    blog_posts = graphene.List(BlogPost)
    info_page = graphene.Field(InfoPage, id=graphene.ID(required=True))
    info_pages = graphene.List(InfoPage)

    def resolve_blog_post(root, info, id, **kwargs):
        return pages_for_device(models.BlogPost.objects, info.context.device).get(id=id)

    def resolve_blog_posts(root, info, **kwargs):
        return (
            pages_for_device(models.BlogPost.objects, info.context.device)
            .filter(locale__language_code=info.context.language)
            .order_by('-first_published_at')
        )

    def resolve_info_page(root, info, id, **kwargs):
        return pages_for_device(models.InfoPage.objects, info.context.device).get(id=id)

    def resolve_info_pages(root, info, **kwargs):
        return (
            pages_for_device(models.InfoPage.objects, info.context.device)
            .filter(locale__language_code=info.context.language)
        )
