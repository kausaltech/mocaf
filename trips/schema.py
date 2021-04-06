from django.utils import timezone
from django.db.models import Q
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
            'id', 'mode', 'mode_confidence', 'start_time', 'end_time', 'start_loc', 'end_loc',
            'length', 'carbon_footprint'
        ]


class TripNode(DjangoNode, AuthenticatedDeviceNode):
    class Meta:
        model = Trip
        fields = ['id', 'legs']

    @gql_optimizer.resolver_hints(
        model_field='legs',
    )
    def resolve_legs(root, info):
        return root.legs.exclude(deleted=True)


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


class UpdateLeg(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        leg = graphene.ID(required=True)
        mode = graphene.ID()
        nr_passengers = graphene.Int()
        deleted = graphene.Boolean()

    leg = graphene.Field(LegNode)
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, leg, mode=None, nr_passengers=None, deleted=None):
        dev = info.context.device

        if mode is not None:
            if mode.isdigit():
                qs = Q(id=mode)
            else:
                qs = Q(identifier=mode)
            try:
                mode_obj = TransportMode.objects.get(qs)
            except TransportMode.DoesNotExist:
                available_modes = ', '.join(TransportMode.objects.values_list('identifier', flat=True))
                raise GraphQLError('Transport mode does not exist. Available modes: %s' % available_modes, [info])
        else:
            mode_obj = None

        update_data = dict(
            mode=mode, nr_passengers=nr_passengers, deleted=deleted
        )

        with transaction.atomic():
            update_fields = []
            try:
                obj = Leg.objects.filter(trip__device=dev, id=leg).select_for_update().get()
            except Leg.DoesNotExist:
                raise GraphQLError('Leg does not exist', [info])

            if mode_obj:
                obj.user_corrected_mode = mode_obj
                obj.mode = mode_obj
                update_fields += ['user_corrected_mode', 'mode']

            if nr_passengers:
                obj.nr_passengers = nr_passengers
                update_fields.append('nr_passengers')

            if update_fields:
                obj.update_carbon_footprint()
                obj.updated_at = timezone.now()
                update_fields += ['carbon_footprint', 'updated_at']
                obj.save(update_fields=update_fields)

            obj.user_updates.create(data=update_data)

        return dict(ok=True, leg=obj)


class Query(graphene.ObjectType):
    trips = graphene.List(TripNode)
    transport_modes = graphene.List(TransportModeNode)

    def resolve_trips(root, info):
        dev = info.context.device
        return gql_optimizer.query(dev.trips.all(), info)

    def resolve_transport_modes(root, info):
        return gql_optimizer.query(TransportMode.objects.all(), info)


class Mutations(graphene.ObjectType):
    enable_mocaf = EnableMocafMutation.Field()
    disable_mocaf = DisableMocafMutation.Field()
    update_leg = UpdateLeg.Field()
