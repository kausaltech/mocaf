from django.utils import timezone
from django.db.models import Q
from django.db import transaction
import graphene
from graphql.error import GraphQLError
import graphene_django_optimizer as gql_optimizer
from mocaf.graphql_types import DjangoNode, AuthenticatedDeviceNode
from mocaf.graphql_helpers import paginate_queryset

from .models import Trip, Leg, Device, TransportMode, InvalidStateError


class TransportModeNode(DjangoNode):
    class Meta:
        model = TransportMode
        fields = [
            'id', 'identifier', 'name'
        ]


class LegNode(DjangoNode, AuthenticatedDeviceNode):
    can_update = graphene.Boolean()

    def resolve_can_update(root: Leg, info):
        return root.can_user_update()

    class Meta:
        model = Leg
        fields = [
            'id', 'mode', 'mode_confidence', 'start_time', 'end_time', 'start_loc', 'end_loc',
            'length', 'carbon_footprint', 'nr_passengers', 'deleted_at',
        ]


class TripNode(DjangoNode, AuthenticatedDeviceNode):
    legs = graphene.List(
        LegNode, offset=graphene.Int(), limit=graphene.Int(), order_by=graphene.String(),
    )
    start_time = graphene.DateTime()
    end_time = graphene.DateTime()
    carbon_footprint = graphene.Float()
    length = graphene.Float()

    class Meta:
        model = Trip
        fields = ['id', 'legs', 'deleted_at']

    @gql_optimizer.resolver_hints(
        model_field='legs'
    )
    def resolve_legs(root, info, **kwargs):
        qs = root.legs.active()
        qs = paginate_queryset(qs, info, kwargs, orderable_fields=['start_time'])
        return qs


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

            if not obj.user_can_update:
                raise GraphQLError('Leg update no longer possible', [info])

            if mode_obj:
                obj.user_corrected_mode = mode_obj
                obj.mode = mode_obj
                update_fields += ['user_corrected_mode', 'mode']

            if nr_passengers:
                obj.nr_passengers = nr_passengers
                update_fields.append('nr_passengers')

            if deleted:
                obj.deleted_at = timezone.now()
                update_fields += ['deleted_at']

            if update_fields:
                obj.update_carbon_footprint()
                obj.updated_at = timezone.now()
                update_fields += ['carbon_footprint', 'updated_at']
                obj.save(update_fields=update_fields)

            obj.user_updates.create(data=update_data)

            if deleted:
                obj.trip.handle_leg_deletion(obj)

            if update_fields:
                obj.trip.update_carbon_footprint()

        return dict(ok=True, leg=obj)


class Query(graphene.ObjectType):
    trips = graphene.List(
        TripNode, offset=graphene.Int(), limit=graphene.Int(),
        order_by=graphene.String(),
    )
    trip = graphene.Field(TripNode, id=graphene.ID(required=True))
    transport_modes = graphene.List(TransportModeNode)

    def resolve_trips(root, info, **kwargs):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        qs = dev.trips.active().annotate_times()
        qs = paginate_queryset(qs, info, kwargs, orderable_fields=['start_time'])
        qs = gql_optimizer.query(qs, info)
        return qs

    def resolve_trip(root, info, id):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        qs = dev.trips.active().annotate_times().filter(id=id)
        qs = gql_optimizer.query(qs, info)
        return qs.first()

    def resolve_transport_modes(root, info):
        return gql_optimizer.query(TransportMode.objects.all(), info)


class Mutations(graphene.ObjectType):
    enable_mocaf = EnableMocafMutation.Field()
    disable_mocaf = DisableMocafMutation.Field()
    update_leg = UpdateLeg.Field()
