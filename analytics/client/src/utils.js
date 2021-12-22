const floatFormatter = new Intl.NumberFormat('fi-FI', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

const intFormatter = new Intl.NumberFormat('fi-FI');


export function formatFloat(num) {
  return floatFormatter.format(num);
}

export function formatDecimal(num) {
  return intFormatter.format(num);
}
