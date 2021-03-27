from django.utils import timezone
from django.db import transaction
import graphene
from graphql.error import GraphQLError
from graphene_gis.converter import gis_converter  # noqa
import graphene_django_optimizer as gql_optimizer

from mocaf.graphql_types import DjangoNode, AuthenticatedDeviceNode
from .models import Trip, Leg, Device, TransportMode, InvalidStateError


class TransportModeNode(DjangoNode):
    class Meta:
        model = TransportMode
        fields = [
            'id', 'identifier', 'name'
        ]


class LegNode(DjangoNode, AuthenticatedDeviceNode):
    class Meta:
        model = Leg
        fields = [
            'id', 'mode', 'mode_confidence', 'started_at', 'ended_at', 'start_loc', 'end_loc',
            'length', 'carbon_footprint'
        ]


class TripNode(DjangoNode, AuthenticatedDeviceNode):
    class Meta:
        model = Trip
        fields = ['id', 'legs']


class EnableMocafMutation(graphene.Mutation):
    class Arguments:
        uuid = graphene.UUID(required=False)

    ok = graphene.Boolean()
    token = graphene.String(required=False)

    @transaction.atomic
    def mutate(root, info, uuid=None):
        dev = info.context.device
        if dev:
            if uuid:
                raise GraphQLError("Specify either uuid or @device directive, not both")
            token = None
        else:
            if not uuid:
                raise GraphQLError("Device uuid required", [info])

            dev = Device.objects.filter(uuid=uuid).first()
            if dev is not None:
                raise GraphQLError("Device exists, specify token with the @device directive", [info])
            dev = Device(uuid=uuid)
            dev.generate_token()
            dev.save()
            token = dev.token

        try:
            dev.set_enabled(True)
        except InvalidStateError:
            raise GraphQLError('Already enabled', [info])

        return dict(ok=True, token=token)


class DisableMocafMutation(graphene.Mutation, AuthenticatedDeviceNode):
    ok = graphene.Boolean()

    def mutate(root, info):
        dev = info.context.device
        try:
            dev.set_enabled(False)
        except InvalidStateError:
            raise GraphQLError('Already disabled', [info])

        return dict(ok=True)


class ClearUserDataMutation(graphene.Mutation, AuthenticatedDeviceNode):
    ok = graphene.Boolean()

    def mutate(root, info, uuid):
        # dev = info.context.device
        return dict(ok=False)


class Query(graphene.ObjectType):
    trips = graphene.List(TripNode)

    def resolve_trips(root, info):
        dev = info.context.device
        return gql_optimizer.query(dev.trips.all(), info)


class Mutations(graphene.ObjectType):
    enable_mocaf = EnableMocafMutation.Field()
    disable_mocaf = DisableMocafMutation.Field()
