import json
import os
from django.conf import settings
from django.contrib.gis.db.models.aggregates import Extent

from django.db import connection
from django.contrib.gis.db.models.functions import Transform
from subprocess import Popen, PIPE

from analytics.models import AreaType, Area


class AreaImporter:
    id: str
    name: str
    is_poi: bool = False

    def get_area_types(self) -> dict:
        raise NotImplementedError()

    def read_area_type(self, identifier: str) -> dict:
        raise NotImplementedError()

    def generate_geojson(self, fc: dict) -> str:
        return json.dumps(fc)

    def generate_topojson(self, fc: dict) -> str:
        print('Computing topology')
        g2t = Popen(
            [os.path.join(settings.BASE_DIR, 'node_modules/.bin/geo2topo')],
            stdin=PIPE, stdout=PIPE, encoding='utf8',
        )
        outs, errs = g2t.communicate(json.dumps(fc))
        assert not errs
        print('Simplifying')
        ts = Popen(
            [os.path.join(settings.BASE_DIR, 'node_modules/.bin/toposimplify'), '-P', '10.0'],
            stdin=PIPE, stdout=PIPE, encoding='utf8'
        )
        outs, errs = ts.communicate(outs)
        assert not errs
        return outs

    def clean_and_simplify(self, area_type: AreaType):
        cursor = connection.cursor()

        print('Cleaning up geometries')
        query = """
            UPDATE analytics_area SET
                geometry = ST_Multi(ST_SimplifyPreserveTopology(geometry, 0.1))
            WHERE NOT ST_IsValid(geometry) AND type_id = %(area_type)s;
        """
        cursor.execute(query, params=dict(area_type=area_type.id))

        query = """
            SELECT COUNT(*) FROM analytics_area
                WHERE type_id = %(area_type)s AND
                    (NOT ST_IsValid(geometry) OR NOT ST_IsValid(ST_Transform(geometry, 4326)))
        """
        cursor.execute(query, params=dict(area_type=area_type.id))
        nr_rows = cursor.fetchone()[0]
        if nr_rows:
            raise Exception('Invalid geometries remain')

        print('Generating GeoJSON')
        areas = list(area_type.areas.all().values('id').annotate(geom=Transform('geometry', 4326)))
        bbox = area_type.areas.all().annotate(
            geom=Transform('geometry', 4326)).aggregate(Extent('geom')
        )['geom__extent']
        feats = [dict(
            type='Feature',
            properties=dict(id=x['id']),
            geometry=json.loads(x['geom'].geojson)
        ) for x in areas]
        fc = dict(type='FeatureCollection', features=feats)

        if not area_type.is_poi:
            topo = self.generate_topojson(fc)
            # open('%s.topojson' % area_type.identifier, 'w').write(topo)
            area_type.topojson = topo
        fc['bbox'] = list(bbox)
        area_type.geojson = self.generate_geojson(fc)
        area_type.save(update_fields=['topojson', 'geojson'])

    def import_area_type(self, identifier: str):
        conf = self.read_area_type(identifier)

        area_type = AreaType.objects.filter(identifier=identifier).first()
        if area_type is None:
            area_type = AreaType(identifier=identifier)
        area_type.name = conf['name']
        if 'name_en' in conf:
            area_type.name_en = conf['name_en']
        area_type.is_poi = conf.get('is_poi', self.is_poi)
        area_type.properties_meta = conf.get('properties_meta')
        area_type.save()

        existing = {a.identifier: a for a in area_type.areas.all()}
        print('Saving')
        for area in conf['areas']:
            obj = existing.pop(area['identifier'], None)
            if obj is None:
                obj = Area(type=area_type, identifier=area['identifier'])
                print('New: %s (%s)' % (area['name'], area['identifier']))
            obj.name = area['name']
            props = area.get('properties', None)
            if props is not None:
                assert isinstance(props, dict)
            obj.properties = props
            obj.geometry = area['geometry']
            if 'centroid' in area:
                obj.centroid = area['centroid']
            else:
                obj.centroid = area['geometry'].centroid
            obj.save()

        for area in existing.values():
            print('Deleted: %s' % area)
            area.delete()

        self.clean_and_simplify(area_type)
