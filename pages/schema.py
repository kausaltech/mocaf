import graphene
from graphene_django import DjangoObjectType

from . import models


class BlogPost(DjangoObjectType):
    class Meta:
        model = models.BlogPost
        only_fields = ['id', 'title', 'tagline', 'body', 'first_published_at']


class Query(graphene.ObjectType):
    blog_post = graphene.Field(BlogPost, id=graphene.Int(required=True))
    blog_posts = graphene.List(BlogPost)

    def resolve_blog_post(self, info, id, **kwargs):
        return models.BlogPost.objects.get(id=id)

    def resolve_blog_posts(self, info, **kwargs):
        return (models.BlogPost.objects
                .live()
                .public()
                .filter(locale__language_code=info.context.language)
                .specific()
                .order_by('-first_published_at'))
