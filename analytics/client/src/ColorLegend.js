import React from 'react';
import chroma from 'chroma-js';
import { formatDecimal, formatFloat } from './utils';


export default function ColorLegend({title, elements}) {
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
  return (
    <div style={style}>
      <table>
        <caption><strong>{title}</strong></caption>
        <tbody>
          { elements.map(([color, value]) => (
            <tr key={value}>
              <td><div style={getElStyle(color)}/></td>
              <td style={{verticalAlign: 'bottom'}}>
                { parseFloat(value) ? formatFloat(value*100) + '%' : value }
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
