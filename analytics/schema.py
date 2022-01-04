from django.db.models.fields import IntegerField
from django.db.models.query_utils import Q
from django.urls import reverse
from graphql.error import GraphQLError
import graphene

from mocaf.graphql_types import DjangoNode

from utils.i18n import resolve_i18n_field
from .models import AreaType, Area, DailyModeSummary, DailyTripSummary


class AreaNode(graphene.ObjectType):
    id = graphene.ID()
    identifier = graphene.ID()
    name = graphene.String()


class PropertyMeta(graphene.ObjectType):
    identifier = graphene.ID()
    description = graphene.String()


class AreaTypeNode(DjangoNode):
    areas = graphene.List(AreaNode)
    topojson_url = graphene.String(required=False)
    geojson_url = graphene.String()
    properties_meta = graphene.List(PropertyMeta)
    # daily_trips_url = graphene.String()
    # daily_lengths_url = graphene.String()
    is_poi = graphene.Boolean()

    def resolve_areas(root, info):
        return root.areas.all().values('id', 'identifier', 'name')

    def resolve_topojson_url(root: AreaType, info):
        request = info.context
        if root.is_poi:
            return None
        url = reverse('area-type-topojson', kwargs=dict(id=root.id))
        return request.build_absolute_uri(url)

    def resolve_geojson_url(root: AreaType, info):
        request = info.context
        if not root.is_poi:
            return None
        url = reverse('area-type-geojson', kwargs=dict(id=root.id))
        return request.build_absolute_uri(url)

    def resolve_daily_trips_url(root: AreaType, info):
        request = info.context
        url = reverse('area-type-stats', kwargs=dict(id=root.id, type='daily-trips'))
        return request.build_absolute_uri(url)

    def resolve_daily_lengths_url(root: AreaType, info):
        request = info.context
        url = reverse('area-type-stats', kwargs=dict(id=root.id, type='daily-lengths'))
        return request.build_absolute_uri(url)

    def resolve_properties_meta(root: AreaType, info):
        if not root.properties_meta:
            return None
        return [dict(identifier=x[0], description=x[1]) for x in root.properties_meta.items()]

    def resolve_name(root: AreaType, info):
        print(root)
        return resolve_i18n_field(root, 'name', info)

    class Meta:
        model = AreaType
        fields = ['id', 'identifier', 'name', 'areas']


class AreaNode(DjangoNode):
    class Meta:
        model = Area
        fields = ['id', 'identifier', 'name']


class DailyTripSummaryNode(graphene.ObjectType):
    date = graphene.Date()
    origin_id = graphene.ID()
    dest_id = graphene.ID()
    mode_id = graphene.ID()
    trips = IntegerField()


class Analytics(graphene.ObjectType):
    area_types = graphene.List(AreaTypeNode)

    def resolve_daily_trips(root, info, area_type):
        area_type = AreaType.objects.get(identifier=area_type)
        return list(DailyTripSummary.objects.filter(origin__type=area_type, dest__type=area_type).values(
            'date', 'origin_id', 'dest_id', 'mode_id', 'trips',
        ))

    def resolve_area_types(root, info):
        return AreaType.objects.all()


class Query(graphene.ObjectType):
    analytics = graphene.Field(Analytics)

    def resolve_analytics(root, info):
        # FIXME: Check API key?
        return Analytics()
