import { useState, useEffect } from 'react';
import { useCubeQuery }  from '@cubejs-client/react';
import * as topojson from 'topojson-client';
import Papa from 'papaparse';
import lodash from 'lodash';
import * as aq from 'arquero';


function useRawData({ url, type }) {
  const [rawData, setRawData] = useState(null);

  useEffect(() => {
    if (!url) return;
    Papa.parse(url, {
      download: true,
      header: true,
      fastMode: true,
      complete: (results) => {
        /*
        let table = aq.from(results.data);
        // Add the derived "weekend" column
        table = table.derive({weekend: (d) => aq.op.includes([0, 6], aq.op.dayofweek(d.date))});
        setRawData(table);
        */
        setRawData(results.data);
      },
      transform: (val, column) => {
        if (column === 'length' || column === 'trips') {
          return parseFloat(val);
        } else if (column === 'date') {
          return new Date(val);
        }
        return val;
      }
    })
  }, [url, type]);
  return rawData;
}

function preprocessLengthsOld(resultSet) {
  const data = resultSet.tablePivot({
    x: ['DailyLengths.areaId'],
    y: ['TransportModes.identifier', 'measures']
  });
  const AREA_ID_KEY = 'DailyLengths.areaId';
  const byArea = Object.fromEntries(data.map((row) => {
    const area = row[AREA_ID_KEY];
    let sum = 0;
    const byMode = {};
    Object.entries(row).forEach(([key, val]) => {
      if (key === AREA_ID_KEY) return;
      byMode[key.split(',')[0]] = val;
      sum += val;
    });
    byMode.total = sum;
    return [area, {absolute: byMode}];
  }));
  Object.values(byArea).forEach((area) => {
    const { absolute } = area;
    area.relative = Object.fromEntries(Object.entries(absolute).map(([mode, length]) => ([mode, length / absolute.total])));
  });
  return byArea;
}

function preprocessLengths(resultSet) {
  let table = aq.from(resultSet.rawData())
    .select({
      'DailyLengths.areaId': 'areaId',
      'TransportModes.identifier': 'mode',
      'DailyLengths.totalLength': 'length',
    })
    .groupby('areaId')
    .pivot('mode', 'length');

  const availableModes = table.columnNames((col) => col != 'areaId');
  table = table
    .derive({
      total: aq.escape(d => lodash.sum(Object.values(lodash.pick(d, availableModes))))
    })
    .derive(Object.fromEntries(availableModes.map(mode =>
      [`${mode}_rel`, aq.escape(d => d[mode] / d.total)]
    )));
  return table;
}

function preprocessTrips(resultSet) {
  let table = aq.from(resultSet.rawData())
    .derive({
      trips: d => aq.op.parse_int(d['DailyTrips.totalTrips'])
    })
    .select({
      'DailyTrips.originId': 'originId',
      'DailyTrips.destId': 'destId',
      'TransportModes.identifier': 'mode',
      'trips': 'trips',
    })
    .filter(d => d.trips >= 5);
  return table;
}

export function useAnalyticsData({ type, areaTypeId, weekend, startDate = '2021-06-01', endDate = '2022-01-01' }) {
  let queryOpts;
  let dateField;

  if (type === 'lengths') {
    queryOpts = {
      measures: ['DailyLengths.totalLength'],
      dimensions: [
        'DailyLengths.areaId',
        'TransportModes.identifier',
      ],
      filters: [{
        member: 'AreaTypes.id',
        operator: 'equals',
        values: [areaTypeId],
      }],
      segments: [],
    }
    if (weekend === true) {
      queryOpts.segments.push('DailyLengths.weekends');
    } else if (weekend === false) {
      queryOpts.segments.push('DailyLengths.weekdays');
    }
    dateField = 'DailyLengths.date';
  } else if (type === 'trips') {
    queryOpts = {
      measures: ['DailyTrips.totalTrips'],
      dimensions: [
        'DailyTrips.originId',
        'DailyTrips.destId',
        'TransportModes.identifier',
      ],
      segments: [],
      filters: [{
        member: 'AreaTypes.id',
        operator: 'equals',
        values: [areaTypeId],
      }, {
        member: 'DailyTrips.totalTrips',
        operator: 'gte',
        values: [5],
      }],
    }
    if (weekend === true) {
      queryOpts.segments.push('DailyTrips.weekends');
    } else if (weekend === false) {
      queryOpts.segments.push('DailyTrips.weekdays');
    }
    dateField = 'DailyTrips.date';
  } else {
    throw new Error('unknown datatype');
  }

  if (startDate) {
    queryOpts.filters.push({
      member: dateField,
      operator: 'gte',
      values: [startDate],
    })
  }
  if (endDate) {
    queryOpts.filters.push({
      member: dateField,
      operator: 'lt',
      values: [endDate],
    })
  }

  const cubeResp = useCubeQuery(queryOpts);
  const { resultSet } = cubeResp;
  if (!resultSet) return;
  if (type === 'lengths') {
    return preprocessLengths(resultSet);
  } else {
    return preprocessTrips(resultSet);
  }
}


export function useAreaTopo(areaType) {
  const [areaData, setAreaData] = useState(null);

  const processTopo = (topo) => {
    const areas = new Map(areaType.areas.map((area) => [area.id, area]));
    const { bbox } = topo;
    const geojson = topojson.feature(topo, topo.objects['-']);
    geojson.features = geojson.features.map((feat) => {
      const area = areas.get(feat.properties.id.toString());
      const out = {
        ...feat,
        properties: {
          ...feat.properties,
          name: area.name,
          identifier: area.identifier,
        },
      };
      return out;
    })
    return { bbox, geojson };
  };

  useEffect(() => {
    fetch(areaType.topojsonUrl)
      .then(res => res.json())
      .then(
        (res) => {
          setAreaData(processTopo(res));
        },
        (error) => {
          console.error(error);
        }
      )
  }, [areaType]);
  return areaData;
};
