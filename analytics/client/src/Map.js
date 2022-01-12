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


function getInitialView(bbox) {
  return {
    longitude: (bbox[0] + bbox[2]) / 2,
    latitude: (bbox[1] + bbox[3]) / 2,
    zoom: 9,
    pitch: 0,
    bearing: 0,
  };
}

function AreaMap({ geoData, getFillColor, getElevation, getTooltip, colorStateKey }) {
  const { bbox, geojson } = geoData;
  const [hoverInfo, setHoverInfo] = useState({});
  const initialView = getInitialView(bbox);
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
      onHover: info => setHoverInfo(info),
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


export function TransportModeShareMap({ areaType, areaData, transportModes, selectedTransportMode , rangeLength}) {
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
    const average = area.data[modeId] / rangeLength;
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
    return { area: {name, identifier}, rel, transportMode: selectedTransportMode?.name, abs, syntheticModes, average };
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
  const [hoverInfo, setHoverInfo] = useState({});
  const poiGeoData = usePoiGeojson(poiType);
  const geoData = useAreaTopo(areaType);
  if (!poiGeoData || !geoData || !areaData) return <Spinner />;

  const { bbox, geojson } = geoData;

  const initialView = getInitialView(bbox);
  const areaTable = aq.from(areaType.areas).derive({areaId: a => op.parse_int(a.id)})
  const popupData = {
    poiId: hoverInfo.object?.properties.id
  }
  let topFiveAreas;
  if (popupData.poiId) {
    topFiveAreas = areaData
      .params({poiId: popupData.poiId})
      .filter((d, $) => d.poiId === $.poiId)
      .select('areaId', 'isInbound', 'trips')
      .orderby('isInbound', aq.desc('trips'))
      .groupby('isInbound')
      .slice(0, 5)
      .lookup(areaTable, ['areaId', 'areaId'], 'name', 'identifier');
  }

  const layers = [
    new GeoJsonLayer({
      id: 'area-layer',
      data: geojson,
      pickable: true,
      stroked: true,
      filled: true,
      //extruded: !!getElevation,
      getFillColor: [255, 255, 255, 0],
      getLineColor: [0, 0, 0, 40],
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 2,
      //getElevation,
      // updateTriggers: {
      //   getFillColor: colorStateKey
      // }
    }),
    new GeoJsonLayer({
      id: 'poi-layer',
      data: poiGeoData,
      pickable: true,
      stroked: true,
      filled: true,
      //extruded: !!getElevation,
      getFillColor: [255, 255, 255, 200],
      getLineColor: [127, 0, 0, 200],
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 3,
      onHover: info => setHoverInfo(info),
      // updateTriggers: {
      //   getFillColor: [
      //     this.state.hoveredObject
      //       ? this.state.hoveredObject.properties.id
      //       : null
      //   ]
      // },
      // onHover: info => setHoverInfo(info),
      //getElevation,
      // updateTriggers: {
      //   getFillColor: colorStateKey
      // }
    }),

  ];
  const groups = topFiveAreas?.groupby('isInbound')
        .objects({grouped: true})

  return (
    <div>
      <Layer>
        <div style={{position: 'fixed', bottom: '100px', left: '10px', width: '600px', height: '300px'}}>
          { groups ? [false, true].map(inbound => {
            const group = groups.get(inbound);
            if (group == null) {
              return;
            }
            return (<table style={{float: 'left'}}>
                     <caption>
                       { inbound ? 'Top 5 lähtöpaikat' : 'Top 5 kohteet'}
                     </caption>
                     { group.map(row => (
                         <tr>
                           <td>{row.name}</td>
                           <td>{row.trips}</td>
                         </tr>
                       ))
                     }
                    </table>);
          }) : null}
        </div>
      </Layer>
    <DeckGL initialViewState={initialView}
            controller={true}
            layers={layers}>
      <StaticMap reuseMaps
                 mapStyle={MAP_STYLE}
                 preventStyleDiffing={true}
                 mapboxApiAccessToken={MAPBOX_ACCESS_TOKEN} />
    </DeckGL>
    </div>
  );
}
