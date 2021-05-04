import graphene
from graphene_django import DjangoObjectType

from . import models


class BlogPost(DjangoObjectType):
    class Meta:
        model = models.BlogPost
        only_fields = ['id', 'title', 'body']


class Query(graphene.ObjectType):
    page = graphene.Field(BlogPost, id=graphene.Int(required=True))
    pages = graphene.List(BlogPost)

    def resolve_page(self, info, id, **kwargs):
        return models.BlogPost.objects.get(id=id)

    def resolve_pages(self, info, **kwargs):
        return models.BlogPost.objects.live().public().filter(depth__gt=1).specific()
