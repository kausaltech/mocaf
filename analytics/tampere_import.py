import json
import io
import geopandas as gpd
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.conf import settings
from owslib.wfs import WebFeatureService

from .models import AreaType, Area


def read_wfs_layer(wfs_url, wfs_typename):
    wfs = WebFeatureService(url=wfs_url, version='2.0.0')
    layer = wfs[wfs_typename]
    crs = str(layer.crsOptions[0])
    out = wfs.getfeature(typename=wfs_typename, outputFormat='json')

    d = json.load(out)
    return d


def import_areas():
    area_type = AreaType.objects.filter(identifier='tre:tilastoalue').first()
    if area_type is None:
        area_type = AreaType.objects.create(identifier='tre:tilastoalue', name='Tilastoalue')

    d = read_wfs_layer(
        'http://geodata.tampere.fi/geoserver/wfs',
        'hallinnolliset_yksikot:KH_TILASTO'
    )
    crs = d['crs']['properties']['name']
    srs = SpatialReference(crs)
    local_srs = SpatialReference(settings.LOCAL_SRS)
    ct = CoordTransform(srs, local_srs)
    for feat in d['features']:
        props = feat['properties']
        geom = GEOSGeometry(json.dumps(feat['geometry']))
        geom.srid = srs.srid
        geom.transform(ct)
        area = Area.objects.filter(identifier=props['TUNNUS']).first()
        if area is not None:
            continue
        name = props['NIMI']
        parts = name.split(' ')
        parts[0] = parts[0].capitalize()
        name = ' '.join(parts)
        area = Area(type=area_type, identifier=props['TUNNUS'], name=name, geometry=geom)
        area.save()
        print(area)

    """
        update analytics_area SET
            geometry = ST_SimplifyPreserveTopology(geometry, 0.01)
        WHERE NOT ST_IsValid(geometry);
    """
