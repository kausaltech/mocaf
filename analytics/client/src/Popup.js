import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Block } from 'baseui/block';
import { formatFloat, formatDecimal } from './utils';

export function Popup ({y, x, children, title, maxWidth}) {
  const popupWidth = maxWidth ?? 150;
  const adaptedX = Math.min(window.innerWidth - popupWidth, x);
  return <div style={{
                position: 'absolute',
                top: y,
                left: adaptedX,
                pointerEvents: 'none',
                backgroundColor: 'white',
                borderRadius: '0.5em',
                boxShadow: '5px 5px 5px #00000033'
              }}>
           <Block style={{ padding: '0.5em' }}>
             <div style={{ marginBottom: '0.5em' }}>
               { title }
             </div>
             { children }
           </Block>
         </div>
}

export function AreaPopup ({y, x, children, rel, area, abs, transportMode, syntheticModes, average}) {
  const { t } = useTranslation();
  if (area == null) {
    return null;
  }
  const title = <>
                  <strong>{area.name}</strong> {area.identifier && `(${area.identifier})`}
                </>

  const contents = <div>
               <strong>{transportMode}</strong> - {t('transport-mode-share')}<br/>
               <FigureElement {...{rel, average, syntheticModes}} />
               {children}
             </div>
  return <Popup x={x} y={y} children={contents} title={title} maxWidth={320}/>
}

function FigureElement ({rel, average, syntheticModes}) {
  const { t } = useTranslation();
  if (isNaN(rel)) {
    return t('no-data');
  }

  const syntheticFigures = (syntheticModes ?? []).map(m =>
    <div key={m.name} style={{fontSize: '80%'}}>{
      `${m.name}: ` + (isNaN(m.rel) ? t('no-data') : `${formatFloat(m.rel)} %`)
    }</div>);
  return <>
           {t('traveled-kilometers-share')} <strong>{formatFloat(rel)} %</strong>
           {average != 0 && !isNaN(average) && ` (${formatDecimal(average)} ${t('kilometers-per-day')})`}
           {syntheticFigures}
         </>
}
