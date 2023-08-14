# pylint: disable=no-self-argument
from datetime import timedelta
from typing import Any

import graphene
import graphene_django_optimizer as gql_optimizer
import sentry_sdk
from django.contrib.gis.geos import LineString
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from graphql.error import GraphQLError

from budget.enums import EmissionUnit, TimeResolution
from budget.models import EmissionBudgetLevel
from mocaf.graphql_gis import LineStringScalar, PointScalar
from mocaf.graphql_helpers import GraphQLNeedConfirmation, paginate_queryset
from mocaf.graphql_types import AuthenticatedDeviceNode, DjangoNode, DjangoObjectType
from trips_ingest.models import Location

from .models import (
    AlreadyRegistered, BackgroundInfoQuestion, Device, DeviceDefaultModeVariant, InvalidStateError, Leg, LegLocation,
    MigrationRequired, TransportMode, TransportModeVariant, Trip
)
from utils.i18n import resolve_i18n_field


class TransportModeVariantNode(DjangoNode):
    def resolve_name(root: TransportModeVariant, info):
        return resolve_i18n_field(root, 'name', info)

    class Meta:
        model = TransportModeVariant
        fields = [
            'id', 'identifier', 'name', 'emission_factor',
        ]


class TransportModeNode(DjangoNode):
    default_variant = graphene.Field(TransportModeVariantNode)

    def resolve_name(root: TransportModeVariant, info):
        return resolve_i18n_field(root, 'name', info)

    class Meta:
        model = TransportMode
        fields = [
            'id', 'identifier', 'name', 'variants', 'emission_factor',
        ]


class LegLocationNode(DjangoNode, AuthenticatedDeviceNode):
    loc = PointScalar()

    class Meta:
        model = LegLocation
        fields = [
            'loc', 'time'
        ]


class LegNode(DjangoNode, AuthenticatedDeviceNode):
    can_update = graphene.Boolean()
    geometry = LineStringScalar()

    def resolve_can_update(root: Leg, info):
        return root.can_user_update()

    def resolve_geometry(root: Leg, info):
        if not root.can_user_update():
            points = []
        else:
            points = list(root.locations.active().values_list('loc', flat=True).order_by('time'))
        return LineString(points)

    def resolve_locations(root: Leg, info):
        if not root.can_user_update():
            points = []
        else:
            points = root.locations.active()
        return points

    class Meta:
        model = Leg
        fields = [
            'id', 'mode', 'mode_variant', 'mode_confidence', 'start_time', 'end_time', 'start_loc', 'end_loc',
            'length', 'carbon_footprint', 'nr_passengers', 'deleted_at', 'locations', 'geometry',
        ]


class TripNode(DjangoNode, AuthenticatedDeviceNode):
    legs = graphene.List(
        LegNode, offset=graphene.Int(), limit=graphene.Int(), order_by=graphene.String(),
    )
    start_time = graphene.DateTime()
    end_time = graphene.DateTime()
    carbon_footprint = graphene.Float()
    budget_level_impact = graphene.Float(
        description='How much does this trip reduce the remaining carbon budget for the month?'
    )
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

    def resolve_budget_level_impact(root, info, **kwargs):
        monthly_budget = info.context.monthly_budget[root.start_time.date()]
        footprint = root.carbon_footprint
        val = -footprint / monthly_budget
        return val


class ConfigNode(AuthenticatedDeviceNode):
    sensor_sampling_delay = graphene.Int(description='Accelerometer and gyroscope sampling delay in min (disable if <= 0)')
    sensor_sampling_distance = graphene.Int(description='Sample sensors only after having moved this many meters from last sampling location')
    sensor_sampling_period = graphene.Int(description='How many ms to poll for sensors')


class EnableMocafMutation(graphene.Mutation):
    class Arguments:
        uuid = graphene.String(required=False)

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
            if dev is None:
                dev = Device(uuid=uuid)
            else:
                if dev.token:
                    raise GraphQLError("Device exists, specify token with the @device directive", [info])
            dev.generate_token()
            dev.mocaf_enabled = True
            dev.save()
            token = dev.token

        try:
            dev.set_enabled(True)
        except InvalidStateError:
            raise GraphQLError('Already enabled', [info])

        return dict(ok=True, token=token)

class EnableSurveyMutation(graphene.Mutation):
    class Arguments: 
        uuid = graphene.String(required=False)
    ok = graphene.Boolean()
    def mutate(root, info, uuid):
        dev = Device.objects.get(uuid=uuid)
        if (dev.survey_enabled == True):
            dev.survey_enabled = False
        else:
            dev.survey_enabled = True
        dev.save()
        return dict(ok=True)


class EnableCarbonMutation(graphene.Mutation):
    class Arguments: 
        uuid = graphene.String(required=False)
    ok = graphene.Boolean()
    def mutate(root, info, uuid):
        dev = Device.objects.get(uuid=uuid)
        if (dev.mocaf_enabled == True):
            dev.mocaf_enabled = False
        else:
            dev.mocaf_enabled = True
        dev.save()
        return dict(ok=True)


class DisableMocafMutation(graphene.Mutation, AuthenticatedDeviceNode):
    ok = graphene.Boolean()

    def mutate(root, info):
        dev = info.context.device
        try:
            dev.set_enabled(False)
        except InvalidStateError:
            sentry_sdk.capture_exception(GraphQLError('Mocaf already disabled', [info]))

        return dict(ok=True)


class ClearUserDataMutation(graphene.Mutation, AuthenticatedDeviceNode):
    ok = graphene.Boolean()

    def mutate(root, info):
        dev = info.context.device
        now = timezone.now()
        with transaction.atomic():
            dev.trips.all().delete()
            # Rows in compressed hypertable chunks can't be deleted
            # Location.objects.filter(uuid=dev.uuid).update(deleted_at=now)
            dev.receive_data.all().delete()
            dev.delete()

        return dict(ok=True)


class RegisterDeviceMutation(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        account_key = graphene.String()
        confirm_device_migration = graphene.Boolean(required=False, default_value=False)

    ok = graphene.Boolean()

    def mutate(root, info, account_key, confirm_device_migration):
        device = info.context.device
        try:
            device.register(account_key, migrate_existing=confirm_device_migration)
        except MigrationRequired as e:
            raise GraphQLNeedConfirmation(str(e))
        return dict(ok=True)


class UpdateLeg(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        leg = graphene.ID(required=True)
        mode = graphene.ID()
        mode_variant = graphene.ID()
        nr_passengers = graphene.Int()
        deleted = graphene.Boolean()

    leg = graphene.Field(LegNode)
    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, leg, mode=None, mode_variant=None, nr_passengers=None, deleted=None):
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

            if not obj.can_user_update():
                raise GraphQLError('Leg update no longer possible', [info])

            if mode_obj:
                obj.user_corrected_mode = mode_obj
                obj.mode = mode_obj
                # Check if we need to reset the mode variant
                if not mode_variant and obj.mode_variant is not None:
                    available_variants = list(mode_obj.variants.all())
                    if obj.mode_variant not in available_variants:
                        obj.mode_variant = None
                        update_fields += ['mode_variant']
                update_fields += ['user_corrected_mode', 'mode']
            else:
                mode_obj = obj.mode

            if mode_variant:
                try:
                    variant_obj = mode_obj.variants.get(identifier=mode_variant)
                except TransportModeVariant.DoesNotExist:
                    raise GraphQLError('Variant not found for mode %s' % mode_obj.identifier, [info])

                obj.mode_variant = variant_obj
                obj.user_corrected_mode_variant = variant_obj
                update_fields += ['mode_variant', 'user_corrected_mode_variant']

            if nr_passengers is not None:
                obj.nr_passengers = nr_passengers
                update_fields.append('nr_passengers')

            if deleted:
                obj.deleted_at = timezone.now()
                update_fields += ['deleted_at']

            if update_fields:
                obj.update_carbon_footprint()
                obj.updated_at = timezone.now()
                update_fields += ['carbon_footprint', 'updated_at']
                obj.save(update_fields=set(update_fields))

            obj.user_updates.create(data=update_data)

            if deleted:
                obj.trip.handle_leg_deletion(obj)

            if update_fields:
                obj.trip.update_device_carbon_footprint()

        return dict(ok=True, leg=obj)


class SetDefaultTransportModeVariant(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        mode = graphene.ID(required=True)
        variant = graphene.ID(required=False)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, mode, variant=None):
        dev = info.context.device
        try:
            mode_obj = TransportMode.objects.get(identifier=mode)
        except TransportMode.DoesNotExist:
            available_modes = ', '.join(TransportMode.objects.values_list('identifier', flat=True))
            raise GraphQLError('Transport mode does not exist. Available modes: %s' % available_modes, [info])

        if not mode_obj.variants.exists():
            raise GraphQLError('Transport mode %s does not support variants' % mode_obj.identifier)

        default_obj = DeviceDefaultModeVariant.objects.filter(device=dev, mode=mode_obj).first()
        if variant is None:
            if default_obj is not None:
                default_obj.delete()
            return dict(ok=True)

        try:
            variant_obj = TransportModeVariant.objects.get(identifier=variant)
        except TransportModeVariant.DoesNotExist:
            available_variants = ', '.join(mode_obj.variants.all().values_list('identifier', flat=True))
            raise GraphQLError(
                'Variant %s for %s does not exist. Available variants: %s' % (
                    variant, mode_obj.identifier, available_variants
                ), [info]
            )

        if default_obj is None:
            default_obj = DeviceDefaultModeVariant(device=dev, mode=mode_obj)
        default_obj.variant = variant_obj
        default_obj.save()

        return dict(ok=True)


def set_emission_budget_levels(info, qs):
    if not qs:
        info.context.monthly_budget = {}
        return

    min_time = min([x.start_time for x in qs])
    max_time = max([x.start_time for x in qs])
    level = (
        EmissionBudgetLevel.objects.filter(year__lte=min_time.year)
        .order_by('-year', '-carbon_footprint').first()
    )
    if level is None:
        info.context.monthly_budget = {}
        return

    date = min_time.date()
    end_date = max_time.date()
    levels = {}
    while date <= end_date:
        amount = level.calculate_for_date(
            date, time_resolution=TimeResolution.MONTH, units=EmissionUnit.G
        )
        levels[date] = amount
        date += timedelta(days=1)
    info.context.monthly_budget = levels


class DeviceQuery(DjangoObjectType):
    class Meta:
        model = Device
        field = ("uuid", "survey_enabled", "mocaf_enabled", "enabled_at", "disabled_at", "created_at", "last_processed_data_received_at")

class Query(graphene.ObjectType):
    trips = graphene.List(
        TripNode, offset=graphene.Int(), limit=graphene.Int(),
        order_by=graphene.String(),
    )
    trip = graphene.Field(TripNode, id=graphene.ID(required=True))
    transport_modes = graphene.List(TransportModeNode)
    config = graphene.Field(ConfigNode)
    device_data = graphene.Field(DeviceQuery)

    def resolve_device_data(root, info):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        return Device.objects.get(uuid=dev.uuid)

    def resolve_config(root, info):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        return dict(sensor_sampling_delay=15, sensor_sampling_distance=500, sensor_sampling_period=3000)

    def resolve_trips(root, info, **kwargs):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        qs = dev.trips.active().annotate_times()
        qs = paginate_queryset(qs, info, kwargs, orderable_fields=['start_time'])
        qs = gql_optimizer.query(qs, info)
        set_emission_budget_levels(info, qs)
        return qs

    def resolve_trip(root, info, id):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])
        qs = dev.trips.active().annotate_times().filter(id=id)
        qs = gql_optimizer.query(qs, info)
        obj = qs.first()
        if obj is None:
            return None
        set_emission_budget_levels(info, [obj])
        return obj

    def resolve_transport_modes(root, info):
        dev = info.context.device
        modes = TransportMode.objects.all().prefetch_related('variants')
        if dev is not None:
            defaults = {x.mode_id: x.variant for x in dev.default_mode_variants.select_related('variant')}
            for mode in modes:
                mode.default_variant = defaults.get(mode.id)

        return modes

class BackgroundQuestionInput(graphene.InputObjectType):
    question_id = graphene.ID(required=True)
    answer = graphene.String(required=False)


class UpdateBackgroundInfo(graphene.Mutation, AuthenticatedDeviceNode):
    class Arguments:
        questions = graphene.List(BackgroundQuestionInput)

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info, questions):
        dev = info.context.device
        with transaction.atomic():
            dev.background_info_questions.all().delete()
            new_objs = []
            for q in questions:
                new_objs.append(BackgroundInfoQuestion(
                    device=dev,
                    question=q.question_id,
                    answer=q.answer
                ))
            BackgroundInfoQuestion.objects.bulk_create(new_objs)
        return dict(ok=True)


class Mutations(graphene.ObjectType):
    enable_mocaf = EnableMocafMutation.Field()
    disable_mocaf = DisableMocafMutation.Field()
    update_background_info = UpdateBackgroundInfo.Field()
    clear_user_data = ClearUserDataMutation.Field()
    register_device = RegisterDeviceMutation.Field()
    set_default_transport_mode_variant = SetDefaultTransportModeVariant.Field()
    update_leg = UpdateLeg.Field()
    enable_survey = EnableSurveyMutation.Field()
    enable_carbon = EnableCarbonMutation.Field()
