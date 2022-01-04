import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Block } from 'baseui/block';
import { formatFloat, formatDecimal } from './utils';

export default function Popup ({y, x, children, rel, area, abs, transportMode}) {
  const { t } = useTranslation();
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
               <strong>{transportMode}</strong> - {t('transport-mode-share')}<br/>
               <FigureElement {...{rel, abs}} />
               {children}
             </div>
           </Block>
         </div>
}

function FigureElement ({rel, abs}) {
  const { t } = useTranslation();
  if (isNaN(rel)) {
    return t('no-data');
  }
  return <React.Fragment>
           {t('traveled-kilometers-share')} <strong>{formatFloat(rel)} %</strong>
           {abs != 0 && !isNaN(abs) && ` (${formatDecimal(abs)} km)`}
         </React.Fragment>
}
