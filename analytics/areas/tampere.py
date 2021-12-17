from .wfs import WFSImporter
from .paavo import PaavoImporter


class TamperePaavoImporter(PaavoImporter):
    id = 'tampere_paavo'
    name = 'Pirkanmaa Postal Areas'
    area_types = {
        'tre:paavo': dict(name='Pirkanmaan postinumeroalueet'),
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
            layer='hallinnolliset_yksikot:KH_TILASTO'
        ),
        'tre:suunnittelualue': dict(
            name='Tampereen suunnittelualueet',
            layer='hallinnolliset_yksikot:KH_SUUNNITTELUALUE'
        ),
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
            areas.append(dict(identifier=props['TUNNUS'], name=name, geometry=feat['geometry']))

        return dict(identifier=identifier, name=conf['name'], areas=areas)
