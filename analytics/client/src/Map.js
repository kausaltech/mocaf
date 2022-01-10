import React, { useState, useCallback, useEffect } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { StaticMap } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import { Layer } from 'baseui/layer';
import chroma from 'chroma-js';
import numbro from 'numbro';
import * as aq from 'arquero';

import 'maplibre-gl/dist/maplibre-gl.css';

import { useAreaTopo, usePoiGeojson } from './data';
import Popup from './Popup.js';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';


function AreaMap({ geoData, getFillColor, getElevation, getTooltip, colorStateKey }) {
  const { bbox, geojson } = geoData;
  const [hoverInfo, setHoverInfo] = useState({});
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
      onHover: info => setHoverInfo(info), // FIXME: memoize other components than popup
      //getElevation,
      updateTriggers: {
        getFillColor: colorStateKey
      }
    })
  ];

  const popupValues = getTooltip(hoverInfo) ?? {};
  return (
    <div>
      { hoverInfo.object && (
        <Layer>
          <Popup
            x={hoverInfo.x}
            y={hoverInfo.y}
            {...popupValues}
          />
        </Layer>
      )}
      <DeckGL
        initialViewState={initialView}
        controller={true}
        layers={layers}
        >
          <StaticMap reuseMaps mapStyle={MAP_STYLE} preventStyleDiffing={true} mapboxApiAccessToken={MAPBOX_ACCESS_TOKEN} />
      </DeckGL>
    </div>
  );
}


export function TransportModeShareMap({ areaType, areaData, transportModes, selectedTransportMode }) {
  const geoData = useAreaTopo(areaType);
  if (!geoData) return <Spinner />;

  const modeId = selectedTransportMode.identifier;
  const modeById = new Map(transportModes.map(m => [m.identifier, m]));
  const areasById = new Map(areaType.areas.map(area => [parseInt(area.id), {...area}]))

  let getFillColor = d => [0, 0, 0, 0];
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
    const limits = chroma.limits(relativeVals, 'q', 7);
    const scales = chroma.scale([selectedTransportMode.colors.zero, selectedTransportMode.colors.primary]).classes(limits);

    getElevation = (d) => {
      const id = d.properties.id;
      const area = areasById.get(id);
      const val = area.data[modeId];
      return (val - minLength) / (maxLength - minLength) * 5000;
    };
    getFillColor = (d) => {
      const id = d.properties.id;
      const area = areasById.get(id);
      if (!area.data) return [0, 0, 0, 0];
      const val = area.data[modeId + '_rel'];
      const abs = area.data[modeId];
      if (abs < 100) return [0, 0, 0, 0];
      return [...scales(val).rgb(), 220];
    },
    colorStateKey = modeId;
  }
  const getTooltip = ({object}) => {
    if (!object) return null;
    const { id, name, identifier } = object.properties;
    const area = areasById.get(id);
    if (!area.data) return null;
    const rel = area.data[modeId + '_rel'] * 100;
    const abs = area.data[modeId];
    const syntheticModes = [
      {
        name: modeById.get('walk_and_bicycle').name,
        rel: area.data['walk_and_bicycle_rel'] * 100,
      },
      {
        name: modeById.get('public_transportation').name,
        rel: area.data['public_transportation_rel'] * 100,
      }
    ];
    return { area: {name, identifier}, rel, transportMode: selectedTransportMode?.name, abs, syntheticModes };
  };
  return (
    <AreaMap
      geoData={geoData}
      getFillColor={getFillColor}
      colorStateKey={colorStateKey}
      getTooltip={getTooltip}
    />
  );
}


export function POIMap({ poiType, areaType, areaData, transportModes, selectedTransportMode }) {
  const poiGeoData = usePoiGeojson(poiType);
  const geoData = useAreaTopo(areaType);
  if (!poiGeoData || !geoData || !areaData) return <Spinner />;

  areaData.print();

  return <div />;
}
