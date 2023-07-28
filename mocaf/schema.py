import graphene
from graphql import DirectiveLocation
from graphql.type import (
    GraphQLArgument, GraphQLNonNull, GraphQLString, GraphQLDirective,
    specified_directives
)
from . import graphql_gis  # noqa

from trips import schema as trips_schema
from budget import schema as budget_schema
from feedback import schema as feedback_schema
from pages import schema as pages_schema
from analytics import schema as analytics_schema
from poll import schema as poll_schema


class Mutations(trips_schema.Mutations, feedback_schema.Mutations, poll_schema.Mutations):
    pass


class Query(trips_schema.Query, budget_schema.Query, pages_schema.Query, analytics_schema.Query, poll_schema.Query):
    pass


class DeviceDirective(GraphQLDirective):
    def __init__(self):
        super().__init__(
            name='device',
            description='Select device',
            args={
                'uuid': GraphQLArgument(
                    type_=GraphQLNonNull(GraphQLString),
                    description='Device UUID'
                ),
                'token': GraphQLArgument(
                    type_=GraphQLString,
                    description='Device authentication token'
                ),
            },
            locations=[DirectiveLocation.QUERY, DirectiveLocation.MUTATION]
        )


class LocaleDirective(GraphQLDirective):
    def __init__(self):
        super().__init__(
            name='locale',
            description='Select locale in which to return data',
            args={
                'lang': GraphQLArgument(
                    type_=GraphQLNonNull(GraphQLString),
                    description='Selected language'
                )
            },
            locations=[DirectiveLocation.QUERY]
        )


schema = graphene.Schema(
    query=Query,
    mutation=Mutations,
    directives=specified_directives + [DeviceDirective(), LocaleDirective()],
)
