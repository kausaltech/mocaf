import numbro from 'numbro';

export function formatFloat(num) {
  return numbro(num).format({mantissa: 1});
}

export function formatDecimal(num) {
  return numbro(num).format({mantissa: 0, thousandSeparated: true});
}
