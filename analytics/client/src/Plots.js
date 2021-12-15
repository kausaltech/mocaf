import React from 'react';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import Plot from 'react-plotly.js';
import * as aq from 'arquero';
import lodash from 'lodash';


export function OriginDestinationMatrix({ transportModes, areaType, areaData, mode }) {
  const areasById = new Map(areaType.areas.map((area) => [parseInt(area.id), area]));

  let table = areaData
    .params({ mode: mode.identifier })
    .filter((d, $) => d.mode ==  $.mode)
    .derive({
      originId: aq.escape(d => (areasById.get(d.originId)?.name || 'other')),
      destId: aq.escape(d => (areasById.get(d.destId)?.name || 'other'))
    })
    .filter((d) => (d.originId != 'other' || d.destId != 'other'));

  let selectedAreas = new Set(
    table
      .groupby('originId')
      .rollup({
        total: aq.op.sum('trips')
      })
      .orderby(aq.desc('total'))
      .slice(0, 30)
      .array('originId')
  );

  window._table = table;
  window.aq = aq;
  window.lodash = lodash;
  table = table
    .select('originId', 'destId', 'trips')
    .filter(aq.escape(d => selectedAreas.has(d.originId) && selectedAreas.has(d.destId)))
    .groupby('originId')
    .pivot('destId', { trips: d => aq.op.sum(d.trips) })
    .orderby(aq.desc('originId'))
  const cols = table.array('originId');
  table = table.select(['originId', ...cols]);
  const data = [{
    x: cols,
    y: cols,
    z: cols.map((col) => table.array(col)),
    type: 'heatmap',
    hoverongaps: false
  }];
  const config = {
    responsive: true,
    editable: false,
    //autosizable: true,
  };
  const layout = {
    //autosize: true,
    margin: {
      l: 110,
      r: 20,
      t: 20,
      b: 110,
    },
    xaxis: {
      showgrid: false,
    },
    yaxis: {
      showgrid: false,
    }
  };
  return (
    <Plot
      data={data}
      layout={layout}
      config={config}
      useResizeHandler
      style={{height: '100%', width: '2000px'}} />
  );
} 

export function TransportModesPlot({ transportModes, areaType, areaData }) {
  const modeById = new Map(transportModes.map(m => [m.identifier, m]));
  const areasById = new Map(areaType.areas.map(area => [parseInt(area.id), {...area}]))

  if (!areaData)
    return <Spinner />;

  const availableModes = areaData.columnNames((col) => modeById.has(col));
  const traces = availableModes.map((mode) => {
    const x = [], y = [];
    areaData.objects().forEach(row => {
      const { areaId } = row;
      const area = areasById.get(areaId);
      if (!area) {
        console.warn('area not found');
        return;
      }
      y.push(area.name);
      x.push(row[mode + '_rel'] * 100);
    });
    const trace = {
      name: modeById.get(mode).name,
      orientation: 'h',
      type: 'bar',
      x,
      y,
    };
    return trace;
  })
  const layout = {
    barmode: 'stack',
  };
  const config = {
    responsive: true,
    editable: false,
    autosizable: true,
  };
  console.log(traces);
  return (
    <Plot
      data={traces}
      layout={layout}
      config={config}
      useResizeHandler
      style={{height: '100%', width: '100%'}} />
  );
}
