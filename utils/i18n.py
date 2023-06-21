from typing import Any

def resolve_i18n_field(obj: Any, field_name: str, info):
    if getattr(obj, 'i18n', None) is None:
        return getattr(obj, field_name)
    lang = getattr(info.context, 'language', None)
    if lang is not None:
        lang_key = '%s_%s' % (field_name, lang)
        lang_val = obj.i18n.get(lang_key, None)
        if lang_val:
            return lang_val
    return getattr(obj, field_name)
