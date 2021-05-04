from datetime import date, timedelta
from trips.schema import TransportModeNode
import graphene
from graphql.error import GraphQLError
from django.utils import timezone
from .models import EmissionBudgetLevel
from .enums import TimeResolution, EmissionUnit
from mocaf.graphql_types import DjangoNode, AuthenticatedDeviceNode


class EmissionUnitEnum(graphene.Enum):
    class Meta:
        enum = EmissionUnit
        name = 'EmissionUnit'


class TimeResolutionEnum(graphene.Enum):
    class Meta:
        enum = TimeResolution
        name = 'TimeResolution'


class TransportModeFootprint(graphene.ObjectType):
    mode = graphene.Field(TransportModeNode)
    carbon_footprint = graphene.Float()
    length = graphene.Float()


class CarbonFootprintSummary(graphene.ObjectType):
    date = graphene.Date()
    time_resolution = graphene.Field(TimeResolutionEnum)
    per_mode = graphene.List(TransportModeFootprint, order_by=graphene.String())
    carbon_footprint = graphene.Float()
    length = graphene.Float()
    ranking = graphene.Int()
    maximum_rank = graphene.Int()

    def resolve_carbon_footprint(root, info):
        amount = 0
        for mode in root['per_mode']:
            amount += mode['carbon_footprint']
        return amount

    def resolve_length(root, info):
        amount = 0
        for mode in root['per_mode']:
            amount += mode['length']
        return amount

    def resolve_ranking(root, info):
        return 123

    def resolve_maximum_rank(root, info):
        return 1234

    def resolve_per_mode(root, info, order_by=None):
        if order_by is not None:
            descending = False
            if order_by[0] == '-':
                descending = True
                order_by = order_by[1:]
            if order_by != 'length':
                raise GraphQLError("Invalid order requested", [info])
            root['per_mode'] = sorted(root['per_mode'], key=lambda x: x['length'], reverse=descending)
        return root['per_mode']


class EmissionBudgetLevelNode(DjangoNode):
    """Mobility emission budget to reach different prize levels"""
    date = graphene.Date()

    class Meta:
        model = EmissionBudgetLevel
        fields = [
            'identifier', 'name', 'carbon_footprint', 'year'
        ]


class Query(graphene.ObjectType):
    emission_budget_levels = graphene.List(
        EmissionBudgetLevelNode,
        time_resolution=TimeResolutionEnum(),
        units=EmissionUnitEnum(),
        for_date=graphene.Date(),
    )

    carbon_footprint_summary = graphene.List(
        CarbonFootprintSummary,
        start_date=graphene.Date(required=True),
        end_date=graphene.Date(),
        time_resolution=TimeResolutionEnum(),
        units=EmissionUnitEnum(),
        description="Carbon footprint summary per transport mode"
    )

    def resolve_emission_budget_levels(
        root, info, time_resolution=None, units=None, for_date=None
    ):
        if for_date is None:
            for_date = date.today()

        if time_resolution is None:
            time_resolution = TimeResolution.YEAR
        else:
            time_resolution = TimeResolution(time_resolution)

        if units is None:
            units = EmissionUnit.KG
        else:
            units = EmissionUnit(units)

        year = for_date.year
        levels = list(EmissionBudgetLevel.objects.filter(year=year))
        for level in levels:
            level.carbon_footprint = level.calculate_for_date(
                for_date, time_resolution, units
            )
            level.date = for_date

        return levels

    def resolve_carbon_footprint_summary(
        root, info, start_date, end_date=None, time_resolution=None, units=None
    ):
        dev = info.context.device
        if not dev:
            raise GraphQLError("Authentication required", [info])

        if units is None:
            units = EmissionUnit.KG
        else:
            units = EmissionUnit(units)

        if time_resolution is None:
            time_resolution = TimeResolution.DAY
        else:
            time_resolution = TimeResolution(time_resolution)

        if end_date is not None:
            if start_date > end_date:
                raise GraphQLError("startDate must be less than or equal to endDate", [info])

        summary = dev.get_carbon_footprint_summary(
            start_date, end_date, time_resolution, units
        )
        return [dict(time_resolution=time_resolution, **x) for x in summary]
