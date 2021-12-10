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

const WeekSubsetControl = ({weekSubset}) => (
  <FormControl label="Include">
    <Select value={[WEEK_SUBSETS.find((d) => d.value === weekSubset.value)]}
            clearable={false}
            options={WEEK_SUBSETS}
            labelKey="label"
            valueKey="value"
            onChange={({value}) => { weekSubset.set(value[0].value); }}
    />
  </FormControl>
);

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
    <WeekSubsetControl weekSubset={userChoices.weekSubset} />
  </Block>
);

export default Controls;
