from datetime import date
from trips.schema import TransportModeNode
import graphene
from django.utils import timezone
from .models import EmissionBudgetLevel, TimeResolution, EmissionUnit
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


class CarbonFootprintSummary(AuthenticatedDeviceNode):
    date = graphene.Date()
    time_resolution = graphene.Field(TimeResolution)
    footprint_per_mode = graphene.List(TransportModeFootprint)



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
