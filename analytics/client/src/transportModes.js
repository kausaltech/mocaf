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
  }
}

export default function preprocessTransportModes(originalTransportModes) {
  let transportModes = originalTransportModes.filter((m) => m.identifier !== 'still');
  return transportModes.map((mode) => {
    return (Object.assign({}, mode, {colors: colors[mode.identifier]}));
  });
}
