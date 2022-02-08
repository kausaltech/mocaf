import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Block } from 'baseui/block';
import { formatFloat, formatDecimal } from './utils';

export function Popup ({y, x, children, title, maxWidth, weekSubset}) {
  const { t } = useTranslation();
  const popupWidth = maxWidth ?? 150;
  const adaptedX = Math.min(window.innerWidth - popupWidth, x + 15);
  const weekSubsetName = (
    (weekSubset === true) ? t('weekends') :
    (weekSubset === false) ? t('workdays') :
    t('all-days')
  );

  return (
    <div style={{
           position: 'absolute',
           top: y + 15,
           left: adaptedX,
           marginBottom: 10,
           pointerEvents: 'none',
           backgroundColor: 'white',
           borderRadius: '0.5em',
           minWidth: 500,
           boxShadow: '5px 5px 5px #00000033'
         }}>
      <Block style={{ padding: '0.5em' }}>
        <div style={{ marginBottom: '0.5em' }}>
          { title } <span style={{fontSize: '80%'}}>{ weekSubsetName }</span>
        </div>
        { children }
      </Block>
    </div>
  );
}

export function AreaPopup ({y, x, children, rel, area, abs, transportMode, syntheticModes, average, weekSubset}) {
  const { t } = useTranslation();
  if (area == null) {
    return null;
  }
  const title = (
    <><strong>{area.name}</strong> {area.identifier && `(${area.identifier})`}</>
  );
  const contents = (
    <div>
      <strong>{transportMode}</strong> - {t('transport-mode-share')}<br/>
      <FigureElement {...{rel, average, syntheticModes}} />
      {children}
    </div>
  );
  return <Popup weekSubset={weekSubset} x={x} y={y} children={contents} title={title} maxWidth={320}/>
}

export function AreaToAreaPopup ({y, x, children, rel, area, abs, transportMode, weekSubset, selectedArea}) {
  const { t } = useTranslation();
  if (area == null) {
    return null;
  }
  const title = (
    <><strong>{selectedArea?.name} &mdash; {area.name}</strong> {area.identifier && `(${area.identifier})`}</>
  );

  const contents = (
    <div>
      <strong>{transportMode}</strong> - {t('transport-mode-share')}<br/>
      <TripFigureElement {...{rel, abs}} />
      {children}
    </div>
  );
  return <Popup weekSubset={weekSubset} x={x} y={y} children={contents} title={title} maxWidth={320}/>
}

function TripFigureElement ({rel, abs, syntheticModes}) {
  const { t } = useTranslation();
  if (isNaN(rel) || rel == null || abs == null) {
    return t('no-data');
  }
  return (
    <>
      {t('traveled-trips-share')} <strong>{formatFloat(rel)} % </strong>
      <span style={{fontSize:'80%'}}>({formatDecimal(abs)} {t('trips-total')})</span>
    </>
  );
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
  return (
    <>
      {t('traveled-kilometers-share')} <strong>{formatFloat(rel)} %</strong>
      {average != 0 && !isNaN(average) && ` (${formatFloat(average)} ${t('kilometers-per-day')})`}
      {syntheticFigures}
    </>
  );
}
