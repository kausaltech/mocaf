from django.db import connection
from django.contrib.gis.db.models.aggregates import Extent, GeoAggregate
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from .base import AreaImporter
from .pois import POIS
from analytics.models import AreaType



FIXES = {
    'Rautatieasema': 'Tampereen rautatieasema',
    'Linja-autoasema': 'Tampere linja-autoasema',
}

for src, dest in FIXES.items():
    POIS.remove((src, None))
    POIS.append((dest, None))


BUFFER_RADIUS = 50

def get_query(table_name, order_clause):
    return f"""
        SELECT osm_id, name, ST_Buffer(way, {BUFFER_RADIUS}), ST_Centroid(way)
            FROM {table_name}
            WHERE
                ((%s is not null AND osm_id = %s) OR name = %s)
                AND way && ST_MakeEnvelope(%s, %s, %s, %s, 3067)
            {order_clause}
    """

class TamperePOIImporter(AreaImporter):
    id = 'tampere_poi'
    name = 'Tampere Points of Interest'
    is_poi = True
    area_types = {
        'tre:poi': dict(name='Tampereen kiintopisteet'),
    }

    def get_area_types(self) -> dict:
        return self.area_types

    def read_area_type(self, identifier) -> dict:
        bbox_area_type = AreaType.objects.get(identifier='tre:tilastoalue')
        bbox = bbox_area_type.areas.aggregate(Extent('geometry'))['geometry__extent']
        cursor = connection.cursor()
        areas = []
        for name, osm_id in POIS:
            query = get_query('planet_osm_polygon', 'ORDER BY ST_Area(way) ASC')
            cursor.execute(query, params=(osm_id, osm_id, name, *bbox))
            rows = cursor.fetchall()
            if not len(rows):
                query = get_query('planet_osm_point', '')
                cursor.execute(query, params=(osm_id, osm_id, name, *bbox))
                rows = cursor.fetchall()

            if not len(rows):
                print('%s: no match' % name)
            else:
                print('%s: match' % name)
                if len(rows) != 1:
                    print(rows)
                    print('Too many matches for %s' % name)
                row = rows[0]
                poly = GEOSGeometry(row[2])
                areas.append(dict(
                    name=name,
                    identifier=str(row[0]),
                    geometry=MultiPolygon(poly),
                    centroid=row[3],
                ))

        conf = self.area_types[identifier]
        return dict(
            identifier=identifier,
            name=conf['name'],
            areas=areas,
            is_poi=True,
        )
