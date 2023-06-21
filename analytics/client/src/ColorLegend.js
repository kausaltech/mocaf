import React from 'react';
import chroma from 'chroma-js';
import { formatDecimal, formatFloat } from './utils';


export default function ColorLegend({title, elements}) {
  if (elements == null || elements.length == 0) {
    return null;
  }
  const style = {
    position: 'absolute',
    fontSize: 12,
    bottom: 20,
    left: 20,
    padding: 10,
    minWidth: 100,
    backgroundColor: 'white'
  };
  const elStyle = {
    width: 12,
    height: 12,
    marginTop: 5,
    borderStyle: 'solid',
    borderWidth: 1,
  };
  const getElStyle = (color) => (
    Object.assign({}, elStyle, {
      backgroundColor: color,
      borderColor: chroma(color).darken().hex()
    })
  );
  let elementPairs = elements;
  if (parseFloat(elements[0][1])) {
    elementPairs = elements.map((el, idx, arr) => {
      if (idx === arr.length - 1) {
        return;
      }
      return [el[0], [el[1], arr[idx+1][1]]];
    }).filter(el => el != null).reverse();
  }
  const formatValuePair = (value) => {
    const x = value.map(
      (v, i) => (<span key={i}>{parseFloat(v) ? formatFloat(v*100) : v}</span>));
    x.splice(1, 0, <span key='none'>&ndash;</span>);
    return x;
  };
  const formatValue = (value) => (Array.isArray(value) ? formatValuePair(value) : value);
  return (
    <div style={style}>
      <table>
        <caption style={{textAlign: 'left'}}><strong>{title}</strong></caption>
        <tbody>
          { elementPairs.map(([color, value]) => {
            let key = color;
            if (Array.isArray(value)) {
              key += '-' + value.join('-');
            }
            else {
              key += '-' +  value;
            }
            return <tr key={key}>
              <td style={{width: 14}}><div style={getElStyle(color)}/></td>
              <td style={{textAlign: 'left', verticalAlign: 'bottom'}}>
                { formatValue(value) }
              </td>
            </tr>
          })}
        </tbody>
      </table>
    </div>
  );
}
