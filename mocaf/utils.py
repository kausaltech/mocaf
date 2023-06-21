from typing import Iterable, List

from django.db import models


def public_fields(
    model: models.Model,
    add_fields: Iterable[str] = None,
    remove_fields: Iterable[str] = None
) -> List[str]:
    fields = model.public_fields
    if remove_fields is not None:
        fields = [f for f in fields if f not in remove_fields]
    if add_fields is not None:
        fields += add_fields
    return fields
