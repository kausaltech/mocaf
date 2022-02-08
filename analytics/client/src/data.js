import { useState, useEffect, useMemo } from 'react';
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

function preprocessLengths(resultSet, transportModes) {
  const [syntheticModes, primaryModes] = lodash.partition(transportModes, m => m.synthetic);

  let availableModes = primaryModes.map(m => m.identifier)
  let table = aq.from(resultSet.rawData())
    .select({
      'DailyLengths.areaId': 'areaId',
      'TransportModes.identifier': 'mode',
      'DailyLengths.totalLength': 'length',
    })
    .derive({
      length: d => d.length / 1000,  // convert to km
    })
    .groupby('areaId')
    .pivot('mode', 'length')
    .derive({
      total: aq.escape(d => lodash.sum(Object.values(lodash.pick(d, availableModes))))
    });

  for (mode of syntheticModes) {
    table = table.derive({[mode.identifier]: aq.escape(
      d => lodash.sum(Object.values(lodash.pick(d, mode.components))))});
  }
  table = table
    .derive(Object.fromEntries(transportModes.map(mode =>
      [`${mode.identifier}_rel`, aq.escape(d => d[mode.identifier] / d.total)]
    )));
  return table;
}

function preprocessTrips(resultSet, selectedArea, transportModes) {
  const [syntheticModes, primaryModes] = lodash.partition(transportModes, m => m.synthetic);
  let availableModes = primaryModes.map(m => m.identifier)
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
    .params({selectedArea: selectedArea})
    .filter(d => d.trips >= 5)
    .filter((d, $) => (
      $.selectedArea === d.destId ||
      $.selectedArea === d.originId))
    .impute({originId: d => 'unknown',
             destId: d => 'unknown',
             mode: d => 'other'})
    .derive({areaId: (d, $) => d.originId === $.selectedArea ? d.destId : d.originId})
    .groupby('areaId')
    .pivot('mode', {value: d => aq.op.sum(d.trips)})
    .derive({
      total: aq.escape(d => lodash.sum(Object.values(lodash.pick(d, availableModes))))
    });

  for (mode of syntheticModes) {
    table = table.derive({[mode.identifier]: aq.escape(
      d => lodash.sum(Object.values(lodash.pick(d, mode.components))))});
  }
  table = table
    .derive(Object.fromEntries(transportModes.map(mode =>
      [`${mode.identifier}_rel`, aq.escape(d => d[mode.identifier] / d.total)]
    )));
  return table;
}

function preprocessPoiTrips(resultSet) {
  let table = aq.from(resultSet.rawData())
    .impute({ 'TransportModes.identifier': () => 'other' })
    .derive({
      trips: d => aq.op.parse_int(d['DailyPoiTrips.totalTrips'])
    })
    .select({
      'DailyPoiTrips.poiId': 'poiId',
      'DailyPoiTrips.areaId': 'areaId',
      'DailyPoiTrips.isInbound': 'isInbound',
      'TransportModes.identifier': 'mode',
      'DailyPoiTrips.totalLength': 'length',
      'trips': 'trips',
    })
    .derive({
      length: d => d.length / 1000,  // convert to km
    });
  return table;
}

export function useAnalyticsData({ type, areaTypeId, poiTypeId, weekend, startDate, endDate, transportModes, selectedArea }) {
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
        values: ["5"],
      }],
    }
    if (weekend === true) {
      queryOpts.segments.push('DailyTrips.weekends');
    } else if (weekend === false) {
      queryOpts.segments.push('DailyTrips.weekdays');
    }
    dateField = 'DailyTrips.date';
  } else if (type === 'poi_trips') {
    queryOpts = {
      measures: ['DailyPoiTrips.totalTrips', 'DailyPoiTrips.totalLength'],
      dimensions: [
        'DailyPoiTrips.poiId',
        'DailyPoiTrips.areaId',
        'DailyPoiTrips.isInbound',
        'TransportModes.identifier',
      ],
      segments: [],
      filters: [{
        member: 'PoiTypes.id',
        operator: 'equals',
        values: [poiTypeId],
      }, {
        member: 'AreaTypes.id',
        operator: 'equals',
        values: [areaTypeId],
      }, {
        member: 'DailyPoiTrips.totalTrips',
        operator: 'gte',
        values: ["5"],
      }],
    }
    if (weekend === true) {
      queryOpts.segments.push('DailyPoiTrips.weekends');
    } else if (weekend === false) {
      queryOpts.segments.push('DailyPoiTrips.weekdays');
    }
    dateField = 'DailyPoiTrips.date';
  } else {
    throw new Error(`unknown datatype: ${type}`);
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
  const cubeResp = useCubeQuery(queryOpts, {
    skip: false,
    resetResultSetOnChange: true,
  });
  const { previousQuery, resultSet, isLoading } = cubeResp;
  if (isLoading || !resultSet || previousQuery.measures[0] !== queryOpts.measures[0]) return;
  if (type === 'lengths') {
    return preprocessLengths(resultSet, transportModes);
  } else if (type === 'trips') {
    return preprocessTrips(resultSet, selectedArea, transportModes);
  } else if (type === 'poi_trips') {
    return preprocessPoiTrips(resultSet);
  }
}


function processTopo(areaType, topo) {
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
}

let topoCache = {};

export function useAreaTopo(areaType) {
  const [areaData, setAreaData] = useState(null);

  useEffect(() => {
    if (areaType.id in topoCache) {
      setAreaData(topoCache[areaType.id]);
      return;
    }

    fetch(areaType.topojsonUrl)
      .then(res => res.json())
      .then(
        (res) => {
          const data = processTopo(areaType, res);
          topoCache[areaType.id] = data;
          setAreaData(data);
        },
        (error) => {
          console.error(error);
        }
      )
  }, [areaType.id]);
  return areaData;
}

let poiCache = {};

export function usePoiGeojson(poiType) {
  const [poiAreaData, setPoiAreaData] = useState(null);

  useEffect(() => {
    if (poiType.id in poiCache) {
      setPoiAreaData(poiCache[poiType.id]);
      return;
    }

    fetch(poiType.geojsonUrl)
      .then(res => res.json())
      .then(
        (res) => {
          topoCache[poiType.id] = res;
          setPoiAreaData(res);
        },
        (error) => {
          console.error(error);
        }
      )
  }, [poiType.id]);
  return poiAreaData;
}
