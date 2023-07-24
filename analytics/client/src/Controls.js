import React, { useEffect, useState } from 'react';

import {Select} from 'baseui/select';
import {StyledLink} from 'baseui/link'
import {FormControl} from 'baseui/form-control';
import {Slider} from 'baseui/slider';
import {format, parseISO, differenceInCalendarMonths, addMonths, setDate, lastDayOfMonth} from 'date-fns';
import { useTranslation } from 'react-i18next';
import { el } from 'date-fns/locale';

const t = (s) => s;  // Helper for IDE i18n extension to recognize translations

const defaultDateBounds = [
  new Date(2023, 6, 1), new Date(2023, 10, 1)]

const selectionValues = {
  weekSubset: [
    {value: true, label: t('weekends')},
    {value: false, label: t('workdays')},
    {value: null, label: t('all-days')}
  ],
  analyticsQuantity: [
    {value: 'lengths', label: t('transportation-kms')},
    {value: 'trips', label: t('trips')},
    {value: 'poi_trips', label: t('poi-trips')},
  ],
  visualisation: [
    {value: 'choropleth-map', label: t('map')},
    {value: 'table', label: t('table')}
  ]
}

const userChoiceSetAction = (key, value) => ({
  type: 'set',
  key: key,
  payload: value
});


function getSelectedValue(opts, key, userChoiceState) {
  return [
    opts.find((d) => (
      d.value === userChoiceState[key]))];
}

function StaticSelectControl ({lookup, label, userChoices: [userChoiceState, dispatch]}) {
  const { t } = useTranslation();
  const opts = selectionValues[lookup].map((e) => ({
    value: e.value,
    label: t(e.label),
  }));
  return <Select clearable={false}
            options={opts}
            labelKey="label"
            valueKey="value"
            value={getSelectedValue(opts, lookup, userChoiceState)}
            onChange={({value}) => (
              dispatch(userChoiceSetAction(lookup, value[0].value)))}
    />
}

function SelectControl (
  {userChoices: [userChoiceState, dispatch], values, lookup}) {
  let value = null;
  if (values) {
    value = [values?.find((d) => d.identifier === userChoiceState[lookup])];
  }
  return <Select clearable={false}
                 options={values || []}
                 disabled={values===undefined}
                 labelKey="name"
                 valueKey="identifier"
                 value={value}
                 onChange={({value}) => (
                   dispatch(userChoiceSetAction(lookup, value[0].identifier)))}
         />
}

function monthFormat(date) {
  return format(date, 'M/yyyy');
}

function DateRangeSlider ({label, userChoices: [{dateRange}, dispatch]}) {
  const { range, bounds } = dateRange;
  const ifBounds = bounds || defaultDateBounds
  const currentRange = [
    differenceInCalendarMonths(range[0], ifBounds[0]),
    differenceInCalendarMonths(range[1], ifBounds[0])];
  const boundsDigest = `${monthFormat(ifBounds[0])}-${monthFormat(ifBounds[1])}`;

  const [value, setValue] = useState({
    sliderValue: currentRange,
    boundsDigest});

  if (value.boundsDigest !== boundsDigest) {
    setValue({
      sliderValue: currentRange,
      boundsDigest
    });
  }

  function valueToLabel (value) {
    return monthFormat(addMonths(ifBounds[0], value));
  }
  function onChange ({value}) {
    value && setValue({sliderValue: value, boundsDigest});
  }
  function onFinalChange ({value}) {
    if (!value) {
      return;
    }
    const start = setDate(addMonths(ifBounds[0], value[0]), 1);
    const end = lastDayOfMonth(addMonths(ifBounds[0], value[1]));
    dispatch(userChoiceSetAction('dateRange', { bounds: ifBounds, range: [start, end] }));
  }
  return (
    <div style={{gridColumn: '1/4', padding: '0px 10px'}} >
      <Slider value={value.sliderValue}
              marks={true}
              onChange={onChange}
              onFinalChange={onFinalChange}
              label={label}
              min={0}
              persistentThumb={true}
              max={differenceInCalendarMonths(ifBounds[1], ifBounds[0])}
              valueToLabel={valueToLabel}
              step={1}
              overrides={{
                InnerThumb: ({$value, $thumbIndex}) => (
                  <div style={{position: 'absolute', top: 30, fontSize: 12}}>
                    {valueToLabel($value[$thumbIndex])}
                  </div>
                ),
                ThumbValue: () => null,
                TickBar: { style: () => ({ display: 'none' })},
                Thumb: { style: () => ({ position: 'relative' })},
              }}
      />
    </div>
  );
}

const Controls = ({userChoices, dynamicOptions}) => {
  const { t } = useTranslation();
  const [ userChoiceState, dispatch ] = userChoices;
  const poiTripsMode = userChoices[0].analyticsQuantity === 'poi_trips';
  const tripsMode = userChoices[0].analyticsQuantity === 'trips';
  let { transportModes } = dynamicOptions;
  transportModes = transportModes.filter(m => m.identifier !=='combined');
  if (userChoiceState.visualisation === 'table') {
    transportModes = transportModes.filter(m => !m.synthetic);
  }
  return (
    <div className='controls'
         style={{
           position: 'fixed',
           top: 20,
           left: '50%',
           transform: 'translateX(-50%)',
           padding: 10,
           display: 'grid',
           gridTemplateColumns: '1fr 1fr 1fr 1fr',
           gap: '4px',
           minWidth: '30%',
           backgroundColor: '#ffffffdd',
           border: `1px solid #eee`,
         }}>
      <div style={{gridColumn: "1/5", color: '#555'}}>
        <h1 style={{ float: 'left', margin: 0, paddingLeft: 4, paddingTop: 10, paddingBottom: 6, fontSize: 16, fontWeight: 'normal', letterSpacing: 1}}>
            {t('site-name')}
        </h1>
        <div style={{float: 'right', fontSize: 12, color: '#AE1E20', paddingTop: 10}}>
          <span style={{}}>ⓘ</span>
          <StyledLink
            href="#"
            onClick={(e) => dispatch({type: 'set', key: 'modalVisible', payload: true})} >
            {t('visualisation-guide')}
          </StyledLink>
        </div>
      </div>
      <StaticSelectControl lookup='analyticsQuantity' userChoices={userChoices} />
      {
        poiTripsMode ?
          <Select
            clearable={false}
            disabled={true}
            placeholder={[t('map')]} /> :
          <StaticSelectControl lookup='visualisation' userChoices={userChoices} />
      }
      <StaticSelectControl lookup='weekSubset' userChoices={userChoices} />
      <SelectControl lookup='areaType'
                     userChoices={userChoices}
                     values={dynamicOptions.areaTypes} />
      <DateRangeSlider userChoices={userChoices} />
      {
        (poiTripsMode || (tripsMode && userChoiceState.visualisation === 'table')) ?
          <Select
            clearable={false}
            disabled={true}
            placeholder={[t('all-transport-modes')]} /> :
          <SelectControl
            userChoices={userChoices}
            lookup='transportMode'
            values={transportModes} />
      }
    </div>
  );
}

export default Controls;
