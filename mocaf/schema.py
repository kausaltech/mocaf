import graphene
from graphql.type import (
    GraphQLArgument, GraphQLNonNull, GraphQLString, GraphQLDirective,
    DirectiveLocation, specified_directives
)
from graphene.types import UUID
from trips import schema as trips_schema


class Mutations(trips_schema.Mutations):
    pass


class Query(trips_schema.Query):
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


schema = graphene.Schema(
    query=Query,
    mutation=Mutations,
    directives=specified_directives + [DeviceDirective()],
)
