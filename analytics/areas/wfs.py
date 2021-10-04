import os
import hashlib
import json

from django.conf import settings
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import GEOSGeometry, Polygon, MultiPolygon
from owslib.wfs import WebFeatureService

from .base import AreaImporter


class WFSImporter(AreaImporter):
    wfs_url: str

    def read_wfs_layer(self, wfs_typename) -> dict:
        print('Initializing WFS (%s)' % self.wfs_url)

        h = hashlib.md5(('%s:%s' % (self.wfs_url, wfs_typename)).encode('utf8')).hexdigest()
        cache_fn = 'wfs-%s.geojson' % h
        if os.path.exists(cache_fn):
            d = json.load(open(cache_fn, 'r'))
        else:
            wfs = WebFeatureService(url=self.wfs_url, version='2.0.0')
            print('\tGetting features (%s)' % wfs_typename)
            out = wfs.getfeature(typename=wfs_typename, outputFormat='json')
            d = json.load(out)
            json.dump(d, open(cache_fn, 'w'))

        crs = d['crs']['properties']['name']
        srs = SpatialReference(crs)
        local_srs = SpatialReference(settings.LOCAL_SRS)
        ct = CoordTransform(srs, local_srs)
        for feat in d['features']:
            geom = GEOSGeometry(json.dumps(feat['geometry']))
            if isinstance(geom, Polygon):
                geom = MultiPolygon(geom)
            geom.srid = srs.srid
            geom.transform(ct)
            feat['geometry'] = geom

        return d
