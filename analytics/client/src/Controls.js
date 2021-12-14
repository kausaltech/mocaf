import React, { useEffect, useState } from 'react';

import {Select} from 'baseui/select';
import {Block} from 'baseui/block';
import {FormControl} from 'baseui/form-control';
import {Slider} from 'baseui/slider';

const selectionValues = {
  'weekSubset': [
    {value: 'workday', label: 'workdays only'},
    {value: 'weekend', label: 'weekends only'}
  ],
  'areaType': [
    {value: 5, label: 'Postal code area'},
    {value: 6, label: 'Statistics area'}
  ]}

const userChoiceSetAction = (key, value) => ({
  'type': 'set',
  'key': key,
  'payload': value
});


function getSelectedValue(key, userChoiceState) {
  return [
    selectionValues[key].find((d) => (
      d.value === userChoiceState[key]))];
}

function WeekSubsetControl ({userChoices: [userChoiceState, dispatch]}) {
  const key = 'weekSubset';
  return <FormControl label="Include days">
    <Select clearable={false}
            options={selectionValues[key]}
            labelKey="label"
            valueKey="value"
            value={getSelectedValue(key, userChoiceState)}
            onChange={({value}) => (
              dispatch(userChoiceSetAction(key, value[0].value)))}
    />
  </FormControl>
};

function AreaTypeControl ({userChoices: [userChoiceState, dispatch]}) {
  const key = 'areaType';
  return <FormControl label="Area type">
           <Select clearable={false}
                   options={selectionValues[key]}
                   labelKey="label"
                   valueKey="value"
                   value={getSelectedValue(key, userChoiceState)}
                   onChange={({value}) => (
                     dispatch(userChoiceSetAction(key, value[0].value)))}
           />
  </FormControl>
};

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
    <WeekSubsetControl userChoices={userChoices} />
    <AreaTypeControl userChoices={userChoices} />
    <TransportModeControl
      userChoices={userChoices}
      transportModes={dynamicOptions.transportModes} />
  </Block>
);

export default Controls;
