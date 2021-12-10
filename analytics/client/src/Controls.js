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

function WeekSubsetControl ({setWeekSubset}) {
  [ weekSubset, setWeekSubset ] = useState('workday');

  return <FormControl label="Include">
    <Select value={[WEEK_SUBSETS.find(d => d.value === weekSubset)]}
            clearable={false}
            options={WEEK_SUBSETS}
            labelKey="label"
            valueKey="value"
            onChange={({value}) => { setWeekSubset(value[0].value); }}
    />
  </FormControl>
};

const Controls = ({setWeekSubset}) => (
  <Block className='controls' style={{
    position: 'fixed',
    top: 20,
    left: 20,
    padding: 20,
    width: '200px',
    backgroundColor: 'white',
    border: `1px solid #eee`,
  }}>

    <WeekSubsetControl setWeekSubset={setWeekSubset} />

    <FormControl label="Hour">
      <Slider
        min={0}
        max={23}
        step={1}
        value={[0]}
        onChange={({value}) => setHour(Number(value))}
      />
    </FormControl>
  </Block>
);

export default Controls;
