import pytest
from django.utils.translation import override

from notifications.tests.factories import NotificationTemplateFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('field', ['title', 'body'])
@pytest.mark.parametrize('language', ['fi', 'en'])
def test_notification_template_render_variable(field, language):
    factory_kwargs = {f'{field}_{language}': '{{var}}'}
    template = NotificationTemplateFactory(**factory_kwargs)
    result = template.render(field, language=language, var='foo')
    assert result == 'foo'


@pytest.mark.parametrize('field', ['title', 'body'])
def test_notification_template_render_in_active_language(field):
    languages = ['fi', 'en']
    factory_kwargs = {f'{field}_{language}': '{{var_%s}}' % language for language in languages}
    template = NotificationTemplateFactory(**factory_kwargs)
    render_kwargs = {f'var_{language}': language for language in languages}
    for language in languages:
        with override(language):
            result = template.render(field, **render_kwargs)
            assert result == language


@pytest.mark.parametrize('field', ['title', 'body'])
def test_notification_template_render_all_languages(field):
    languages = ['fi', 'en']
    factory_kwargs = {f'{field}_{language}': '{{ var }}' for language in languages}
    template = NotificationTemplateFactory(**factory_kwargs)
    contexts = {language: {'var': language} for language in languages}
    result = template.render_all_languages(field, contexts)
    assert result == {language: language for language in languages}
