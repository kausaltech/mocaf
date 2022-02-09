from django.db import connection
from django.contrib.gis.db.models.aggregates import Extent, GeoAggregate
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from .base import AreaImporter
from analytics.models import AreaType


POIS = [
    'Aleksanterin kirkko', 'Amurin työläismuseokortteli', 'Arboretum (nimi vielä auki???)',
    'Finlayson', 'Finlaysonin kirkko', 'Kalevan kirkko', 'Kansi ja Areena',
    'Kauppahalli', 'Kehräsaari', 'Keskustori', 'Kulttuuritalo Laikku', 'Laikun lava',
    'Laukontori', 'Linja-autoasema', 'Museokeskus Vapriikki', 'Mustalahti',
    'Näsinneula', 'Ortodoksinen kirkko', 'Pyynikin näkötorni', 'Pyynikin uimahalli',
    'Pyynikintori', 'Tampereen pääkirjasto Metso', 'Ratinan stadion', 'Rautatieasema',
    'Sampolan kirjasto', 'Santalahden tapahtumapuisto', 'Sara Hildenin taidemuseo', 'Särkänniemi',
    'Tallipiha', 'Tammelan stadion', 'Tammelantori', 'Tampereen komediateatteri',
    'Tampereen taidemuseo', 'Tampereen teatteri', 'Tampereen työväenteatteri',
    'Tampereen vanha kirkko', 'Tampere-talo', 'Tullikamarin kulttuurikeskus',
    'Tuomiokirkko', 'Työväenmuseo Werstas', 'Vakoilumuseo', 'Verkaranta',
    'Yliopisto'
]

FIXES = {
    'Rautatieasema': 'Tampereen rautatieasema',
    'Linja-autoasema': 'Tampere linja-autoasema',
}

for src, dest in FIXES.items():
    POIS.remove(src)
    POIS.append(dest)


BUFFER_RADIUS = 50


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
        for name in POIS:
            cursor.execute(f"""
                SELECT osm_id, name, ST_Buffer(way, {BUFFER_RADIUS}), ST_Centroid(way)
                    FROM planet_osm_polygon
                    WHERE
                        name = %s
                        AND way && ST_MakeEnvelope(%s, %s, %s, %s, 3067)
                    ORDER BY
                        ST_Area(way) ASC
            """, params=(name, *bbox)
            )
            rows = cursor.fetchall()
            if not len(rows):
                cursor.execute(f"""
                    SELECT osm_id, name, ST_Buffer(way, {BUFFER_RADIUS}), ST_Centroid(way)
                        FROM planet_osm_point
                        WHERE
                            name = %s
                            AND way && ST_MakeEnvelope(%s, %s, %s, %s, 3067)
                """, params=(name, *bbox))
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
