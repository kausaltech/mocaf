import React, { useEffect, useState } from 'react';

import {Select} from 'baseui/select';
import {Block} from 'baseui/block';
import {FormControl} from 'baseui/form-control';
import {Slider} from 'baseui/slider';
import {format, parseISO, differenceInDays, addDays} from 'date-fns';

const selectionValues = {
  weekSubset: [
    {value: true, label: 'weekends only'},
    {value: false, label: 'workdays only'},
    {value: null, label: 'all days'}
  ],
  areaType: [
    {value: 5, label: 'Postal code area'},
    {value: 6, label: 'Statistics area'}
  ],
  analyticsQuantity: [
    {value: 'lengths', label: 'Length of trips'},
    {value: 'count', label: 'Number of trips'}
  ],
  visualisation: [
    {value: 'choropleth-map', label: 'Map'},
    {value: 'table', label: 'Table'}
  ]
}

const userChoiceSetAction = (key, value) => ({
  type: 'set',
  key: key,
  payload: value
});


function getSelectedValue(key, userChoiceState) {
  return [
    selectionValues[key].find((d) => (
      d.value === userChoiceState[key]))];
}

function StaticSelectControl ({lookup, label, userChoices: [userChoiceState, dispatch]}) {
  return <FormControl label={label}>
    <Select clearable={false}
            options={selectionValues[lookup]}
            labelKey="label"
            valueKey="value"
            value={getSelectedValue(lookup, userChoiceState)}
            onChange={({value}) => (
              dispatch(userChoiceSetAction(lookup, value[0].value)))}
    />
  </FormControl>
}


function TransportModeControl (
  {userChoices: [userChoiceState, dispatch], transportModes}) {
  const key = 'transportMode'
  let value = null;
  if (transportModes) {
    value = [transportModes?.find((d) => d.identifier === userChoiceState[key])];
  }
  return <FormControl label="Mode of transportation">
           <Select clearable={false}
                   options={transportModes || []}
                   disabled={transportModes===undefined}
                   labelKey="name"
                   valueKey="identifier"
                   value={value}
                   onChange={({value}) => (
                     dispatch(userChoiceSetAction(key, value[0].identifier)))}
           />
  </FormControl>
}

function DateRangeSlider ({min, max, label}) {
  const dateExtent = [parseISO(min), parseISO(max)]
  const deltaDays = differenceInDays(dateExtent[1], dateExtent[0])
  const [value, setValue] = useState({start: dateExtent[0], bounds: [0, deltaDays]});

  function valueToLabel (value) {
    result = addDays(dateExtent[0], value);
    return format(result, "d.M.yyyy");
  }
  function onChange ({value}) {
    value && setValue({start: min, bounds: value});
  }
  function onFinalChange ({value}) {
  }
  return (
    <Slider value={value.bounds}
            onChange={onChange}
            onFinalChange={onFinalChange}
            label={label}
            min={0}
            max={deltaDays}
            valueToLabel={valueToLabel}
            step={1}
      />
  );
}

const Controls = ({userChoices, dynamicOptions}) => (
  <Block className='controls'
         style={{
           position: 'fixed',
           top: 20,
           left: 20,
           padding: 20,
           width: '200px',
           backgroundColor: 'white',
           border: `1px solid #eee`,
         }}>
    <StaticSelectControl label='Visualisation' lookup='visualisation' userChoices={userChoices} />
    <StaticSelectControl label='What to visualize' lookup='analyticsQuantity' userChoices={userChoices} />
    <StaticSelectControl label='Days of week' lookup='weekSubset' userChoices={userChoices} />
    <DateRangeSlider label='Date range' min={'2021-01-01'} max={'2021-12-31'} />
    <StaticSelectControl label='Area type' lookup='areaType' userChoices={userChoices} />
    <TransportModeControl
      userChoices={userChoices}
      transportModes={dynamicOptions.transportModes} />
  </Block>
);

export default Controls;
