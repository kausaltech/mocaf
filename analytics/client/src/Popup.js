import React, { useState } from 'react';
import { Block } from 'baseui/block';
import { formatFloat, formatDecimal } from './utils';

export default function Popup ({y, x, children, rel, area, abs, transportMode}) {
  return <div style={{
                position: 'absolute',
                top: y,
                left: x,
                pointerEvents: 'none',
                backgroundColor: 'white',
                borderRadius: '0.5em',
                boxShadow: '5px 5px 5px #00000033'
              }}>
           <Block style={{ padding: '0.5em' }}>
             <strong>
             {area.name} {area.identifier && `(${area.identifier})`}<br/>
             Kulkumuoto-osuus: {transportMode.toLowerCase()}</strong><br/>
             {rel && !isNaN(rel) &&
              `Osuus suoritteesta ${formatFloat(rel)} %`
             }
             {abs && !isNaN(abs) &&
               ` (${formatDecimal(abs)} km)`
             }
             {isNaN(rel) &&
              "Ei tietoja"
             }
             {children}
           </Block>
         </div>
}
