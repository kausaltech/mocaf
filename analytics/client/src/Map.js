import React, { useEffect, useState } from 'react';
import {LineLayer, GeoJsonLayer} from '@deck.gl/layers';
import {StaticMap} from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import chroma from 'chroma-js';
import numbro from 'numbro';

import { useAreaTopo } from './data';


function AreaMap({ geoData, getFillColor, getElevation, getTooltip }) {
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
    })
  ];
  return (
    <div><DeckGL
      initialViewState={initialView}
      controller={true}
      layers={layers}
      getTooltip={getTooltip}
      style={{
        left: '280px',
        width: 'calc(100vw - 280px)'
      }}
    >
      <StaticMap mapboxApiAccessToken={MAPBOX_ACCESS_TOKEN} />
    </DeckGL></div>
  );
}


export function TransportModeShareMap({ areaType, areaData, transportModes, mode }) {
  const geoData = useAreaTopo(areaType);

  const relativeVals = Object.values(areaData).map(({ relative }) => relative[mode.identifier] * 100);
  const absoluteVals = Object.values(areaData).map(({ absolute }) => absolute[mode.identifier]);
  absoluteVals.sort((a, b) => a - b);
  const minLength = absoluteVals[0];
  const maxLength = absoluteVals[absoluteVals.length - 1];
  const limits = chroma.limits(relativeVals, 'q', 8);
  const scales = chroma.scale('RdBu').domain([limits[limits.length - 1], limits[0]]);

  const getElevation = (d) => {
    const id = d.properties.identifier;
    const area = areaData[id];
    const val = area.absolute[mode.identifier];
    return (val - minLength) / (maxLength - minLength) * 5000;
  }

  const getColor = (d) => {
    const id = d.properties.identifier;
    const area = areaData[id];
    const val = area.relative[mode.identifier] * 100;
    return [...scales(val).rgb(), 200];
  };
  const renderTooltip = ({object}) => {
    if (!object) return;
    const { id, name, identifier } = object.properties;
    const area = areaData[identifier];
    const rel = numbro(area.relative[mode.identifier] * 100).format({mantissa: 1});
    const abs = numbro(area.absolute[mode.identifier] / 1000).format({mantissa: 0});
    return {
      html: `
        <div>
          <b>${name}</b> (${identifier})<br />
          ${rel} % (${mode.name}), ${abs} km
        </div>
      `,
    }
  };
  if (!geoData) return <Spinner />;
  return (
    <AreaMap
      geoData={geoData}
      getFillColor={getColor}
      getTooltip={renderTooltip}
    />
  );
}
