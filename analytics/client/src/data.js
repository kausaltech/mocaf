import { useState, useEffect } from 'react';
import { useCubeQuery }  from '@cubejs-client/react';
import * as topojson from 'topojson-client';
import Papa from 'papaparse';
//import * as aq from 'arquero/dist/arquero';


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

function processDailyLengths(resultSet) {
  const data = resultSet.tablePivot({
    x: ['Areas.identifier'],
    y: ['TransportModes.identifier', 'measures']
  });
  const AREA_ID_KEY = 'Areas.identifier';
  const byArea = Object.fromEntries(data.map((row) => {
    const area = row[AREA_ID_KEY];
    let sum = 0;
    const byMode = {};
    Object.entries(row).forEach(([key, val]) => {
      if (key === AREA_ID_KEY) return;
      byMode[key.split(',')[0]] = val;
      sum += val;
    });
    return [area, {absolute: byMode}];
  }));
  Object.values(byArea).forEach((area) => {
    const { absolute } = area;
    const totalLength = Object.values(absolute).reduce((sum, val) => (sum + val));
    area.relative = Object.fromEntries(Object.entries(absolute).map(([mode, length]) => ([mode, length / totalLength])));
    absolute.total = totalLength;
  });
  return byArea;
}

export function useAnalyticsData({ type, weekend, startDate, endDate }) {
  let queryOpts;

  if (type === 'lengths') {
    queryOpts = {
      measures: ['DailyLengths.totalLength'],
      dimensions: [
        'Areas.identifier',
        'TransportModes.identifier',
      ],
      segments: [],
    }
    if (weekend === true) {
      queryOpts.segments.push('DailyLengths.weekends');
    } else if (weekend === false) {
      queryOpts.segments.push('DailyLengths.weekdays');
    }
  } else {
    queryOpts = {
      measures: ['DailyTrips.totalTrips'],
      dimensions: [
        'DailyTrips.originId',
        'DailyTrips.destId',
        'TransportModes.identifier',
      ],
      segments: [
      ],
    }
  }
  const cubeResp = useCubeQuery(queryOpts);
  const { resultSet } = cubeResp;
  if (!resultSet) return;
  if (type === 'lengths') {
    return processDailyLengths(resultSet);
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
