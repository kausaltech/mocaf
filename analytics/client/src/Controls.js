import React, { useEffect, useState } from 'react';

import {Select} from 'baseui/select';
import {Block} from 'baseui/block';
import {FormControl} from 'baseui/form-control';
import {Slider} from 'baseui/slider';

const WEEK_SUBSETS = [
  {value: 'workday', label: 'workdays only'},
  {value: 'weekend', label: 'weekends only'},
  {value: 'all', label: 'all days'}
]

const userChoiceSetAction = (key, value) => ({
  'type': 'set',
  'key': key,
  'payload': value
});


function WeekSubsetControl ({userChoices: [userChoiceState, dispatch]}) {
  const key = 'weekSubset';
  const value = [
    WEEK_SUBSETS.find((d) => (
      d.value === userChoiceState[key]))]
  return <FormControl label="Include">
    <Select clearable={false}
            options={WEEK_SUBSETS}
            labelKey="label"
            valueKey="value"
            value={value}
            onChange={({value}) => (
              dispatch(userChoiceSetAction(key, value[0].value)))}
    />
  </FormControl>
};

const Controls = ({userChoices}) => (
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
  </Block>
);

export default Controls;
