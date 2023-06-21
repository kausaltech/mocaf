from factory import LazyAttribute, SubFactory
from wagtail.core.models import Page
from wagtail.core.rich_text import RichText
from wagtail_factories import PageFactory


class BlogPostIndexFactory(PageFactory):
    class Meta:
        model = 'pages.BlogPostIndex'

    parent = LazyAttribute(lambda obj: Page.get_first_root_node())


class BlogPostFactory(PageFactory):
    class Meta:
        model = 'pages.BlogPost'

    parent = SubFactory(BlogPostIndexFactory)
    title = 'title'
    tagline = 'tagline'
    body = RichText('<p>body</p>')
