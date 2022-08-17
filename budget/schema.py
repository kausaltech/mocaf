from __future__ import annotations

import typing
from datetime import date

import graphene
from graphql.error import GraphQLError
from budget.const import get_risk_change

from mocaf.graphql_types import DjangoNode
from trips.schema import TransportModeNode
from .models import DeviceDailyHealthImpact, EmissionBudgetLevel
from .enums import PrizeLevel, TimeResolution, EmissionUnit, Disease

if typing.TYPE_CHECKING:
    from trips.models import Device


class EmissionUnitEnum(graphene.Enum):
    class Meta:
        enum = EmissionUnit
        name = 'EmissionUnit'


class TimeResolutionEnum(graphene.Enum):
    class Meta:
        enum = TimeResolution
        name = 'TimeResolution'


class DiseaseEnum(graphene.Enum):
    class Meta:
        enum = Disease
        name = 'Disease'


class PrizeLevelEnum(graphene.Enum):
    class Meta:
        enum = PrizeLevel
        name = 'PrizeLevel'


class TransportModeFootprint(graphene.ObjectType):
    mode = graphene.Field(TransportModeNode)
    carbon_footprint = graphene.Float()
    length = graphene.Float()
    duration = graphene.Float()


class SummaryCommon(graphene.Interface):
    date = graphene.Date()
    time_resolution = graphene.Field(TimeResolutionEnum)
    ranking = graphene.Int(required=False)
    maximum_rank = graphene.Int(required=False)
    all_rank_values = graphene.List(graphene.Float, required=False)


class CarbonFootprintSummary(graphene.ObjectType):
    units = graphene.Field(EmissionUnitEnum)
    per_mode = graphene.List(TransportModeFootprint, order_by=graphene.String())
    carbon_footprint = graphene.Float()
    length = graphene.Float()
    current_level = graphene.Field('budget.schema.EmissionBudgetLevelNode')
    average_footprint_used = graphene.Boolean()

    class Meta:
        interfaces = (SummaryCommon,)

    def resolve_average_footprint_used(root, info):
        return False

    def resolve_per_mode(root, info, order_by=None):
        per_mode = list(root['per_mode'].values())
        if order_by is not None:
            descending = False
            if order_by[0] == '-':
                descending = True
                order_by = order_by[1:]
            if order_by != 'length':
                raise GraphQLError("Invalid order requested", [info])
            per_mode = sorted(root['per_mode'], key=lambda x: x['length'], reverse=descending)
        return per_mode

    def resolve_current_level(root, info):
        levels = list(EmissionBudgetLevel.objects.filter(year=root['date'].year))
        for level in levels:
            level.carbon_footprint = level.calculate_for_date(
                root['date'], root['time_resolution'], root['units'],
            )
        levels = sorted(levels, key=lambda level: level.carbon_footprint)
        for level in levels:
            if root['carbon_footprint'] < level.carbon_footprint:
                break
        return level


class DiseaseRiskChange(graphene.ObjectType):
    disease = graphene.Field(DiseaseEnum)
    risk_change = graphene.Float()


class HealthImpactSummary(graphene.ObjectType):
    bicycle_mins = graphene.Float()
    walk_mins = graphene.Float()
    mmeth = graphene.Float(description='Marginal MET hours')
    prize_level = graphene.Field(PrizeLevelEnum)
    disease_risks = graphene.List(DiseaseRiskChange)

    class Meta:
        interfaces = (SummaryCommon,)

    def resolve_bicycle_mins(root, info):
        data = root['per_mode'].get('bicycle')
        if data is None:
            return 0
        return data['duration'] / 60

    def resolve_walk_mins(root, info):
        data = root['per_mode'].get('walk')
        if data is None:
            return 0
        return data['duration'] / 60

    def resolve_disease_risks(root, info):
        out = []
        if root['mmeth'] is None:
            return None
        nr_days = root['nr_days']
        for disease in list(Disease):
            out.append(dict(disease=disease, risk_change=get_risk_change(disease, root['mmeth'], nr_days)))
        return out

    def resolve_prize_level(root: dict, info) -> typing.Optional[PrizeLevel]:
        per_mode = root['per_mode']
        b = per_mode.get('bicycle')
        w = per_mode.get('walk')
        total_mins = b['duration'] / 60 if b else 0
        total_mins += w['duration'] / 60 if w else 0
        if root['time_resolution'] == TimeResolution.DAY:
            total_mins *= 7
        elif root['time_resolution'] == TimeResolution.MONTH:
            total_mins = total_mins / 30.0 * 7
        elif root['time_resolution'] == TimeResolution.YEAR:
            total_mins /= 52.0
        levels = (PrizeLevel.GOLD, PrizeLevel.SILVER, PrizeLevel.BRONZE)
        level: typing.Optional[PrizeLevel]
        for level in levels:
            val = DeviceDailyHealthImpact.PRIZE_LEVEL_MINS_WEEKLY[level]
            if total_mins >= val:
                break
        else:
            level = None
        return level


class HealthPrizeLevel(graphene.ObjectType):
    level = graphene.Field(PrizeLevelEnum)
    time_resolution = graphene.Field(TimeResolutionEnum)
    for_date = graphene.Date()
    activity_mins = graphene.Float()


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
    health_prize_levels = graphene.List(
        HealthPrizeLevel, time_resolution=TimeResolutionEnum(), for_date=graphene.Date(),
    )

    carbon_footprint_summary = graphene.List(
        CarbonFootprintSummary,
        start_date=graphene.Date(required=True),
        end_date=graphene.Date(),
        time_resolution=TimeResolutionEnum(),
        units=EmissionUnitEnum(),
        description="Carbon footprint summary per transport mode"
    )

    health_impact_summary = graphene.List(
        HealthImpactSummary,
        start_date=graphene.Date(required=True),
        end_date=graphene.Date(),
        time_resolution=TimeResolutionEnum(),
        description="Carbon footprint summary per transport mode"
    )
    health_impact_enabled = graphene.Boolean()

    def resolve_health_prize_levels(root, info, time_resolution=None):
        if time_resolution is None:
            time_resolution = TimeResolution.WEEK
        else:
            time_resolution = TimeResolution(time_resolution)

        levels = []
        for level, value in DeviceDailyHealthImpact.PRIZE_LEVEL_MINS_WEEKLY.items():
            if time_resolution == TimeResolution.DAY:
                value /= 7.0
            elif time_resolution == TimeResolution.MONTH:
                value = value / 7.0 * 30
            elif time_resolution == TimeResolution.YEAR:
                value = value * 52
            levels.append(dict(level=level, activity_mins=value, time_resolution=time_resolution))

        return levels

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
        dev: typing.Optional[Device] = info.context.device
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

        summary = dev.get_trip_summary(
            start_date, end_date, time_resolution, units, ranking='carbon'
        )
        return [dict(time_resolution=time_resolution, units=units, **x) for x in summary]

    def resolve_health_impact_summary(
        root, info, start_date, end_date=None, time_resolution=None
    ):
        dev: typing.Optional[Device] = info.context.device
        if dev is None:
            raise GraphQLError("Authentication required", [info])
        if time_resolution is None:
            time_resolution = TimeResolution.DAY
        else:
            time_resolution = TimeResolution(time_resolution)

        if end_date is not None:
            if start_date > end_date:
                raise GraphQLError("startDate must be less than or equal to endDate", [info])

        summary = dev.get_trip_summary(
            start_date, end_date, time_resolution, ranking='health'
        )

        out = [dict(time_resolution=time_resolution, **x) for x in summary]
        return out

    def resolve_health_impact_enabled(root, info):
        dev: typing.Optional[Device] = info.context.device
        if dev is None:
            raise GraphQLError("Authentication required", [info])
        return dev.health_impact_enabled
