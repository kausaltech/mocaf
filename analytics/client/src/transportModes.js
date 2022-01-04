const colors = {
  walk: {
    primary: '#e0b565',
    zero: '#e8edee'
  },
  bicycle: {
    primary: '#477168',
    zero: '#e8edee'
  },
  car: {
    primary: '#b9483d',
    zero: '#e8edee'
  },
  bus: {
    primary: '#5090b2',
    zero: '#e8edee'
  },
  tram: {
    primary: '#cb676c',
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
    primary: '#5090b2',
    zero: '#e8edee'
  },
  walk_and_bicycle: {
    primary: '#477168',
    zero: '#e8edee'
  }
}

export const syntheticModes = [
  {
    identifier: 'public_transportation',
    components: ['bus', 'tram', 'train'],
    name: {
      fi: 'Julkinen liikenne',
      en: 'Public transportation'
    }
  },
  {
    identifier: 'walk_and_bicycle',
    components: ['walk', 'cycle'],
    name: {
      fi: 'Kävely ja pyöräily',
      en: 'Walking and cycling'
    }
  }
]

export default function preprocessTransportModes(transportModes, language) {
  return transportModes
    .filter(
      m => m.identifier !== 'still')
    .concat(
      syntheticModes.map(
        m => Object.assign({}, m, {
          name: (m.name[language] ?? m.name['fi']),
          synthetic: true
        })))
    .map(m =>
      Object.assign({}, m, {
        synthetic: (m.synthetic === true),
        colors: colors[m.identifier]}));
}
