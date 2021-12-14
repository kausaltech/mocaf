import React from 'react';
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
    autosizable: true,
  };
  const layout = {
    autosize: true,
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
      style={{height: '100%', width: '100%'}} />
  );
} 

export function TransportModesPlot({ transportModes, areaType, areaData, mode }) {
}
