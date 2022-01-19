import React, { useState, useCallback, useEffect } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { StaticMap } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { useTranslation } from 'react-i18next';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import { Layer } from 'baseui/layer';
import chroma from 'chroma-js';
import numbro from 'numbro';
import * as aq from 'arquero';

import 'maplibre-gl/dist/maplibre-gl.css';

import { useAreaTopo, usePoiGeojson } from './data';
import { Popup, AreaPopup } from './Popup.js';
import { orderedTransportModeIdentifiers } from './transportModes';

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

const getCursor = ({isHovering, isDragging}) => (
  isHovering ? 'pointer' :
  isDragging ? 'grabbing' :
   'grab'
)

function AreaMap({ geoData, getFillColor, getElevation, getTooltip, colorStateKey, weekSubset }) {
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
          <AreaPopup
            x={hoverInfo.x}
            y={hoverInfo.y}
            weekSubset={weekSubset}
            {...popupValues}
          />
        </Layer>
      )}
      <DeckGL
        initialViewState={initialView}
        controller={true}
        layers={layers}
        getCursor={getCursor}
        >
          <StaticMap reuseMaps mapStyle={MAP_STYLE} preventStyleDiffing={true} mapboxApiAccessToken={MAPBOX_ACCESS_TOKEN} />
      </DeckGL>
    </div>
  );
}


export function TransportModeShareMap({ areaType, areaData, transportModes, selectedTransportMode, rangeLength, weekSubset}) {
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
      weekSubset={weekSubset}
    />
  );
}

function POICounterPartModeBar({row, inbound, scale, transportModes, orderedModeIds}) {
  const currentModes = Object.keys(row.breakdown);
  orderedModeIds = orderedModeIds.filter(m => currentModes.includes(m));
  const specs = orderedModeIds.map((k, index) => ({
    color: transportModes.get(k),
    x: Math.round((100*row.breakdown[k]/scale)) - 1,
    cumulativeX: 0
  }))
  for (let i = 0; i < specs.length - 1; i++) {
    specs[i+1].cumulativeX += 1 + specs[i].x + specs[i].cumulativeX;
  }
  return (
    <tr>
      <td style={{paddingRight: '4px', textAlign: 'right'}}>{row.name}</td>
      <td style={{position: 'relative', width: '100px', borderLeft: '1px solid black'}}>
        {specs.map((spec, index) => (
          <div key={index} style={{
                 position: 'absolute',
                 top: 5, left: `${spec.cumulativeX}px`,
                 width: `${spec.x}px`,
                 height: '15px',
                 backgroundColor: spec.color}} />))
        }
      </td>
    </tr>
  )
}

function POICounterPartsTable({inbound, group, transportModes, orderedModeIds}) {
  const { t } = useTranslation();
  const scale = group[0].total_trips;
  return (<table cellSpacing={0} key={inbound ? 'inbound' : 'outbound'}
                 style={{float: 'left', marginRight: '10px'}}>
            <caption style={{textAlign: 'start', fontWeight: 'bold'}}>
              { inbound ? t('top-origins') : t('top-destinations')}
            </caption>
            <tbody>
              {group.map((row) => (
                <POICounterPartModeBar row={row}
                                       inbound={inbound}
                                       scale={scale}
                                       transportModes={transportModes}
                                       orderedModeIds={orderedModeIds}
                                       key={`${row.poiId}_${row.name}_${inbound}`} />
              ))}
            </tbody>
          </table>)
}

export function POIMap({ poiType, areaType, areaData, transportModes, selectedTransportMode, weekSubset }) {
  const [hoverInfo, setHoverInfo] = useState({});
  const poiGeoData = usePoiGeojson(poiType);
  const geoData = useAreaTopo(areaType);
  const poiById = new Map(poiType.areas.map(a => [Number(a.id), {name: a.name, identifier: a.identifier}]));
  if (!poiGeoData || !geoData || !areaData) return <Spinner />;

  const { bbox, geojson } = geoData;

  const initialView = getInitialView(bbox);
  const areaTable = aq.from(areaType.areas).derive({areaId: a => op.parse_int(a.id)})
  let popupData;
  if (hoverInfo.object != null && hoverInfo.object.properties != null) {
    const poiId = hoverInfo.object.properties.id;
    const poi = poiById.get(poiId);
    if (poi != null) {
      popupData = {
        poiId: poiId,
        poiName: poi.name
      }
    }
  }
  let topFiveAreas;
  if (popupData?.poiId) {
    topFiveAreas = areaData
      .params({poiId: popupData.poiId})
      .filter((d, $) => d.poiId === $.poiId)
      .select('areaId', 'isInbound', 'trips', 'poiId', 'mode')
      .groupby('isInbound', 'areaId')
      .rollup({total_trips: aq.op.sum('trips'),
               breakdown: aq.op.object_agg('mode', 'trips')})
      .ungroup()
      .orderby(aq.desc('total_trips'))
      .groupby('isInbound')
      .slice(0, 5)
      .lookup(areaTable, ['areaId', 'areaId'], 'name', 'identifier');
  }
  const getFillColor = (d) => {
    if (hoverInfo?.object?.properties == null) {
      return [255,255,255,200];
    }
    if (d.properties.id === hoverInfo.object.properties.id) {
      return [255,220,80,150];
    }
    return [255,255,255,200];
  }

  const layers = [
    new GeoJsonLayer({
      id: 'area-layer',
      data: geojson,
      pickable: false,
      stroked: true,
      filled: false,
      getLineColor: [0, 0, 0, 80],
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 2,
    }),
    new GeoJsonLayer({
      id: 'poi-layer',
      data: poiGeoData,
      pickable: true,
      stroked: true,
      filled: true,
      getFillColor,
      getLineColor: [127, 0, 0, 200],
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 3,
      updateTriggers: {
        getFillColor: [
          hoverInfo
            ? hoverInfo?.object?.properties?.id
            : null
        ]
      },
      onHover: info => setHoverInfo(info),
    }),

  ];
  const groups = topFiveAreas?.groupby('isInbound')
        .objects({grouped: true})
  const popupTitle = <strong>{popupData?.poiName}</strong>;
  const popupContents = groups ? [true, false].map(inbound => {
    const group = groups.get(inbound);
    if (group == null) {
      return;
    }
    return <POICounterPartsTable
             inbound={inbound}
             group={group}
             transportModes={new Map(transportModes.map(m => [m.identifier, m.colors.primary]))}
             orderedModeIds={orderedTransportModeIdentifiers(transportModes, 'car')}
           />;
  }) : null;

  return (
    <div>
      <Layer>
        { popupContents && <Popup weekSubset={weekSubset} maxWidth={560} x={hoverInfo.x} y={hoverInfo.y} children={popupContents} title={popupTitle} />}
      </Layer>
    <DeckGL initialViewState={initialView}
            controller={true}
            getCursor={getCursor}
            layers={layers}>
      <StaticMap reuseMaps
                 mapStyle={MAP_STYLE}
                 preventStyleDiffing={true}
                 mapboxApiAccessToken={MAPBOX_ACCESS_TOKEN} />
    </DeckGL>
    </div>
  );
}
