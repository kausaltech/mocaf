import lodash from 'lodash';

const colors = {
  walk: {
    primary: '#e8b455',
    zero: '#e8edee'
  },
  bicycle: {
    primary: '#bf7045',
    zero: '#e8edee'
  },
  car: {
    primary: '#ae1e20',
    zero: '#e8edee'
  },
  bus: {
    primary: '#6b9f88',
    zero: '#e8edee'
  },
  tram: {
    primary: '#397368',
    zero: '#e8edee'
  },
  train: {
    primary: '#abc872',
    zero: '#e8edee'
  },
  other: {
    primary: '#bebfbf',
    zero: '#e8edee'
  },
  public_transportation: {
    primary: '#729e6d',
    zero: '#e8edee'
  },
  walk_and_bicycle: {
    primary: '#c78742',
    zero: '#e8edee'
  }
}

export const syntheticModes = [
  {
    identifier: 'walk_and_bicycle',
    components: ['walk', 'bicycle'],
    name: {
      fi: 'Kävely ja pyöräily',
      en: 'Walking and cycling'
    }
  },
  {
    identifier: 'public_transportation',
    components: ['tram', 'bus', 'train'],
    name: {
      fi: 'Joukkoliikenne',
      en: 'Public transportation'
    }
  },
]

const extender = (ext) => ((o) => (Object.assign({}, o, ext(o))));

export function orderedTransportModeIdentifiers (transportModes, selectedTransportMode) {
  const [syntheticModes, primaryModes] = lodash.partition(transportModes, m => m.synthetic);

  let modeGroups = syntheticModes.map(m => m.components);

  const selected = selectedTransportMode.identifier;
  const groupedPrimaryModes = lodash.flatten(modeGroups);
  const singleModeGroups = primaryModes
    .filter(m => !groupedPrimaryModes.includes(m.identifier))
    .map(m => [m.identifier]);

  modeGroups = modeGroups
    .concat(singleModeGroups)
    .sort((a, b) => (
      a.includes(selected) ? -1 :
      b.includes(selected) ? 1 :
      a.includes('other') ? 1 :
      b.includes('other') ? -1 :
      a.includes('car') ? 1 :
      b.includes('car') ? -1 :
      0));
  return lodash.flatten(modeGroups).sort((a, b) => a === selected ? -1 : 0);

}

export default function preprocessTransportModes(transportModes, language) {
  const translatedSyntheticModes = syntheticModes.map(
    extender(m => ({ synthetic: true,
                     name: m.name[language] ?? m.name['fi'] })));
  return transportModes
    .filter(m => m.identifier !== 'still')
    .map(extender(m => ({ synthetic: false })))
    .concat(translatedSyntheticModes)
    .map(extender(m => ({ colors: colors[m.identifier] })));
}
