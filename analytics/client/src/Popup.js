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
             <div style={{ marginBottom: '0.5em' }}>
               <strong>{area.name}</strong> {area.identifier && `(${area.identifier})`}
             </div>
             <div>
               <strong>{transportMode}</strong> -  kulkumuoto-osuus<br/>
               <FigureElement {...{rel, abs}} />
               {children}
             </div>
           </Block>
         </div>
}

function FigureElement ({rel, abs}) {
  if (isNaN(rel)) {
    return "Ei tietoja";
  }
  else if (rel) {
    return <React.Fragment>
             Osuus suoritteesta <strong>{formatFloat(rel)} %</strong>
             {abs && !isNaN(abs) && ` (${formatDecimal(abs)} km)`}
           </React.Fragment>
  }
}
