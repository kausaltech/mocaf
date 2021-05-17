import graphene
from graphene_django import DjangoObjectType
from wagtail.core.rich_text import expand_db_html

from . import models


class BlogPost(DjangoObjectType):
    class Meta:
        model = models.BlogPost
        fields = ['id', 'title', 'tagline', 'body', 'first_published_at']

    body = graphene.String()

    def resolve_body(root, info):
        return expand_db_html(root.body)


class InfoPage(DjangoObjectType):
    class Meta:
        model = models.InfoPage
        fields = ['id', 'title', 'body']

    body = graphene.String()

    def resolve_body(root, info):
        return expand_db_html(root.body)


class Query(graphene.ObjectType):
    blog_post = graphene.Field(BlogPost, id=graphene.ID(required=True))
    blog_posts = graphene.List(BlogPost)
    info_page = graphene.Field(InfoPage, id=graphene.ID(required=True))
    info_pages = graphene.List(InfoPage)

    def resolve_blog_post(root, info, id, **kwargs):
        return (models.BlogPost.objects
                .live()
                .public()
                .specific()
                .get(id=id))

    def resolve_blog_posts(root, info, **kwargs):
        return (models.BlogPost.objects
                .live()
                .public()
                .filter(locale__language_code=info.context.language)
                .specific()
                .order_by('-first_published_at'))

    def resolve_info_page(root, info, id, **kwargs):
        return (models.InfoPage.objects
                .live()
                .public()
                .specific()
                .get(id=id))

    def resolve_info_pages(root, info, **kwargs):
        return (models.InfoPage.objects
                .live()
                .public()
                .filter(locale__language_code=info.context.language)
                .specific()
                .order_by('-first_published_at'))
