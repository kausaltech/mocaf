from .wfs import WFSImporter
from .paavo import PaavoImporter


class TamperePaavoImporter(PaavoImporter):
    id = 'tampere_paavo'
    name = 'Pirkanmaa Postal Areas'
    area_types = {
        'tre:paavo': dict(name='Pirkanmaan postinumeroalueet',
                          name_en='Pirkanmaa postal code areas'),
    }

    def filter_feature(self, identifier: str, feat: dict) -> bool:
        first_two = int(feat['identifier'][0:2])
        return first_two >= 33 and first_two <= 39


class TampereImporter(WFSImporter):
    id = 'tampere_wfs'
    name = 'City of Tampere WFS'
    wfs_url = 'http://geodata.tampere.fi/geoserver/wfs'

    area_types = {
        'tre:tilastoalue': dict(
            name='Tampereen tilastoalueet',
            name_en='Tampere statistical areas',
            layer='hallinnolliset_yksikot:KH_TILASTO',
            identifier_column='TUNNUS'
        ),
        'tre:suunnittelualue': dict(
            name='Tampereen suunnittelualueet',
            name_en='Tampere planning areas',
            layer='hallinnolliset_yksikot:KH_SUUNNITTELUALUE',
            identifier_column='TUNNUS'
        ),
        'tre:palvelualue': dict(
            name='Tampereen palvelualueet',
            name_en='Tampere service areas',
            layer='hallinnolliset_yksikot:KH_PALVELUALUE',
            identifier_column='NUMERO'
        )
    }

    def get_area_types(self):
        return self.area_types

    def read_area_type(self, identifier) -> dict:
        conf = self.area_types[identifier]
        d = self.read_wfs_layer(conf['layer'])
        areas = []
        for feat in d['features']:
            props = feat['properties']
            name = props['NIMI']
            parts = name.split(' ')
            parts[0] = parts[0].capitalize()
            name = ' '.join(parts)
            _identifier = props[conf['identifier_column']]
            areas.append(dict(identifier=_identifier, name=name, geometry=feat['geometry']))

        return dict(identifier=identifier, name=conf['name'], name_en=conf.get('name_en'), areas=areas)
