import React, { useCallback, useEffect } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { StaticMap } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import chroma from 'chroma-js';
import numbro from 'numbro';
import * as aq from 'arquero';

import 'maplibre-gl/dist/maplibre-gl.css';

import { useAreaTopo } from './data';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';


function AreaMap({ geoData, getFillColor, getElevation, getTooltip, colorStateKey }) {
  const { bbox, geojson } = geoData;
  const initialView = {
    longitude: (bbox[0] + bbox[2]) / 2,
    latitude: (bbox[1] + bbox[3]) / 2,
    zoom: 9,
    pitch: 0,
    bearing: 0,
  };
  const layers = [
    new GeoJsonLayer({
      id: 'area-layer',
      data: geojson,
      pickable: true,
      stroked: true,
      filled: true,
      //extruded: !!getElevation,
      getFillColor: getFillColor,
      getLineColor: [0, 0, 0, 200],
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 2,
      //getElevation,
      updateTriggers: {
        getFillColor: colorStateKey
      }
    })
  ];
  return (
    <div><DeckGL
      initialViewState={initialView}
      controller={true}
      layers={layers}
      getTooltip={getTooltip}
    >
      <StaticMap reuseMaps mapStyle={MAP_STYLE} preventStyleDiffing={true} mapboxApiAccessToken={MAPBOX_ACCESS_TOKEN} />
    </DeckGL></div>
  );
}


export function TransportModeShareMap({ areaType, areaData, transportModes, selectedTransportMode }) {
  const geoData = useAreaTopo(areaType);
  if (!geoData) return <Spinner />;

  const modeId = selectedTransportMode.identifier;
  const modeById = new Map(transportModes.map(m => [m.identifier, m]));
  const areasById = new Map(areaType.areas.map(area => [parseInt(area.id), {...area}]))

  let getFillColor = d => [0, 0, 0, 0];
  let getTooltip = ({ object }) => {
    if (!object) return;
    const { id, name, identifier } = object.properties;
    return {
      html: `
        <div>
          <b>${name}</b> (${identifier})<br />
        </div>
      `
    }
  };
  let getElevation;
  let colorStateKey = `${modeId}-nodata`;

  if (areaData) {
    const availableModes = areaData.columnNames((col) => modeById.has(col));
    if (!availableModes.includes(modeId)) {
      throw new Error('selected transport mode not found in data');
    }
    areaData.objects().forEach((row) => {
      const area = areasById.get(row.areaId);
      if (!area) {
        console.warn('Unknown area in input data', row);
        return;
      }
      area.data = row;
    });
    const absoluteVals = areaData.array(modeId);
    absoluteVals.sort((a, b) => a - b);
    const minLength = absoluteVals[0];
    const maxLength = absoluteVals[absoluteVals.length - 1];
    const relativeVals = areaData.array(`${modeId}_rel`);
    const limits = chroma.limits(relativeVals, 'q', 8);
    const scales = chroma.scale('RdBu').classes(limits);

    getElevation = (d) => {
      const id = d.properties.id;
      const area = areasById.get(id);
      const val = area.data[modeId];
      return (val - minLength) / (maxLength - minLength) * 5000;
    }
    getFillColor = (d) => {
      const id = d.properties.id;
      const area = areasById.get(id);
      const val = area.data[modeId + '_rel'];
      const abs = area.data[modeId];
      if (abs < 100) return [0, 0, 0, 0];
      return [...scales(val).rgb(), 200];
    },
    getTooltip = ({object}) => {
      if (!object) return;
      const { id, name, identifier } = object.properties;
      const area = areasById.get(id);
      const rel = numbro(area.data[modeId + '_rel'] * 100).format({mantissa: 1});
      const abs = numbro(area.data[modeId]).format({mantissa: 0});
      return {
        html: `
          <div>
            <b>${name}</b> (${identifier})<br />
            ${rel} % (${selectedTransportMode.name}), ${abs} km
          </div>
        `,
      }
    };
    colorStateKey = modeId;
  }
  return (
    <AreaMap
      geoData={geoData}
      getFillColor={getFillColor}
      getTooltip={getTooltip}
      colorStateKey={colorStateKey}
    />
  );
}
