from typing import Optional
from graphql import ResolveInfo
from graphql.error import GraphQLError
from graphene.utils.str_converters import to_snake_case
from django.db.models.query import QuerySet

def paginate_queryset(
    qs: QuerySet, info: ResolveInfo, kwargs: dict,
    orderable_fields: list[str] = None,
):
    offset = kwargs.get('offset')
    if offset is None:
        offset = 0
    elif offset < 0:
        raise GraphQLError("Invalid offset", [info])
    limit = kwargs.get('limit')
    if limit is not None:
        if limit < 0:
            raise GraphQLError("Invalid limit", [info])
        qs = qs[offset:offset + limit]
    else:
        qs = qs[offset:]

    order = kwargs.get('order_by')
    if order and orderable_fields:
        ascending = True
        if order.startswith('-'):
            ascending = False
            order = order[1:]
        order = to_snake_case(order)
        if order not in orderable_fields:
            raise GraphQLError("Invalid order requested", [info])
        if not ascending:
            order = '-' + order
        qs = qs.order_by(order)

    return qs
