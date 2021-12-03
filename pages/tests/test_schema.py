import pytest
from wagtail.core.models import Locale
from wagtail_localize.models import LocaleSynchronization

from pages.tests.factories import BlogPostFactory

pytestmark = pytest.mark.django_db


def _create_secondary_locales(settings):
    """Create locales for non-default languages and synchronize them from main locale."""
    assert Locale.objects.count() == 1
    assert not LocaleSynchronization.objects.exists()
    main_locale = Locale.objects.first()
    assert main_locale.language_code == settings.LANGUAGE_CODE
    languages = [language_code for language_code, _ in settings.LANGUAGES]
    for language_code in languages:
        if language_code != main_locale.language_code:
            new_locale = Locale.objects.create(language_code=language_code)
            LocaleSynchronization.objects.create(locale=new_locale, sync_from=main_locale)


def test_blog_posts_all_translations(graphql_client_query_data, uuid, token, settings):
    _create_secondary_locales(settings)
    BlogPostFactory()
    for language_code, _ in settings.LANGUAGES:
        data = graphql_client_query_data(
            '''
            query($uuid: String!, $token: String!, $lang: String!)
            @device(uuid: $uuid, token: $token)
            @locale(lang: $lang)
            {
              blogPosts {
                language
              }
            }
            ''',
            variables={'uuid': uuid, 'token': token, 'lang': language_code}
        )
        expected = {
            'blogPosts': [{
                'language': language_code,
            }]
        }
        assert data == expected


@pytest.mark.parametrize('create_other_locales', [False, True])
def test_blog_posts_without_locale_directive_uses_main_locale(
    graphql_client_query_data, uuid, token, settings, create_other_locales
):
    if create_other_locales:
        _create_secondary_locales(settings)
    post = BlogPostFactory()
    data = graphql_client_query_data(
        '''
        query($uuid: String!, $token: String!)
        @device(uuid: $uuid, token: $token)
        {
          blogPosts {
            id
            language
          }
        }
        ''',
        variables={'uuid': uuid, 'token': token}
    )
    expected = {
        'blogPosts': [{
            'id': str(post.id),
            'language': settings.LANGUAGE_CODE,
        }]
    }
    assert data == expected
