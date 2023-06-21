from django.contrib.gis.db.models.functions import Transform
import graphene
from graphene_django import DjangoObjectType
from django.db.models.fields import IntegerField
from django.urls import reverse
from wagtail.core.rich_text import expand_db_html

from mocaf.graphql_gis import PointScalar
from mocaf.graphql_types import DjangoNode

from utils.i18n import resolve_i18n_field
from .models import AreaType, Area, DailyTripSummary
from pages.models import VisualisationGuidePage


class AreaPropertyNode(graphene.ObjectType):
    property_id = graphene.ID()
    value = graphene.Float()


class AreaNode(graphene.ObjectType):
    id = graphene.ID()
    identifier = graphene.ID()
    name = graphene.String()
    centroid = PointScalar()

    properties = graphene.List(AreaPropertyNode)

    def resolve_properties(root: Area, info):
        props = []
        for prop in root.property_values.all():
            props.append(dict(property_id=prop.property_id, value=prop.value))
        return props

    def resolve_centroid(root: Area, info):
        return root.centroid_wsg84


class PropertyMeta(graphene.ObjectType):
    id = graphene.ID()
    identifier = graphene.ID()
    description = graphene.String()


class AreaTypeNode(DjangoNode):
    areas = graphene.List(AreaNode)
    topojson_url = graphene.String(required=False)
    geojson_url = graphene.String()
    properties_meta = graphene.List(PropertyMeta)
    # daily_trips_url = graphene.String()
    # daily_lengths_url = graphene.String()
    property_values_url = graphene.String(required=False)
    daily_trips_date_range = graphene.List(graphene.Date)
    daily_lengths_date_range = graphene.List(graphene.Date)
    daily_poi_trips_date_range = graphene.List(graphene.Date)
    is_poi = graphene.Boolean()

    def resolve_areas(root, info):
        return root.areas.all()\
            .only('id', 'identifier', 'name', 'type')\
            .prefetch_related('property_values')\
            .annotate(centroid_wsg84=Transform('centroid', 4326))

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

    def resolve_property_values_url(root: AreaType, info):
        if not root.properties_meta.exists():
            return None
        request = info.context
        url = reverse('area-type-stats', kwargs=dict(id=root.id, type='properties'))
        return request.build_absolute_uri(url)

    def resolve_properties_meta(root: AreaType, info):
        return root.properties_meta.all()

    def resolve_name(root: AreaType, info):
        return resolve_i18n_field(root, 'name', info)

    class Meta:
        model = AreaType
        fields = ['id', 'identifier', 'name', 'areas']


class DailyTripSummaryNode(graphene.ObjectType):
    date = graphene.Date()
    origin_id = graphene.ID()
    dest_id = graphene.ID()
    mode_id = graphene.ID()
    trips = IntegerField()


class VisualisationGuidePageNode(DjangoObjectType):
    class Meta:
        model = VisualisationGuidePage
        fields = ['id', 'title', 'body']

    body = graphene.String()

    def resolve_body(root, info):
        return expand_db_html(root.body)


class Analytics(graphene.ObjectType):
    area_types = graphene.List(AreaTypeNode, id=graphene.ID(required=False))
    visualisation_guide = graphene.Field(VisualisationGuidePageNode, id=graphene.ID(required=True))
    visualisation_guides = graphene.List(VisualisationGuidePageNode)

    def resolve_daily_trips(root, info, area_type):
        area_type = AreaType.objects.get(identifier=area_type)
        return list(DailyTripSummary.objects.filter(origin__type=area_type, dest__type=area_type).values(
            'date', 'origin_id', 'dest_id', 'mode_id', 'trips',
        ))

    def resolve_area_types(root, info, id=None):
        types = AreaType.objects.all().prefetch_related('properties_meta')
        if id is not None:
            types = types.filter(id=id)
        return types

    def resolve_visualisation_guide(root, info, id, **kwargs):
        return (VisualisationGuidePage.objects
                .live()
                .public()
                .specific()
                .get(id=id))

    def resolve_visualisation_guides(root, info, **kwargs):
        return (VisualisationGuidePage.objects
                .live()
                .public()
                .filter(locale__language_code=info.context.language)
                .specific()
                .order_by('-first_published_at'))


class Query(graphene.ObjectType):
    analytics = graphene.Field(Analytics)

    def resolve_analytics(root, info):
        # FIXME: Check API key?
        return Analytics()
