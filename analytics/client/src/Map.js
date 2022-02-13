import React, { useState, useCallback, useEffect } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { StaticMap } from 'react-map-gl';
import { useTranslation } from 'react-i18next';
import DeckGL from '@deck.gl/react';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import { Layer } from 'baseui/layer';
import {Select, TYPE} from 'baseui/select';
import chroma from 'chroma-js';
import numbro from 'numbro';
import * as aq from 'arquero';

import 'maplibre-gl/dist/maplibre-gl.css';

import { MAP_STYLE, getInitialView, getCursor } from './mapUtils';
import { useAreaTopo } from './data';
import { AreaPopup, AreaToAreaPopup } from './Popup';
import ColorLegend from './ColorLegend';



function AreaMap({ geoData, getFillColor, getElevation, getTooltip, colorStateKey, weekSubset, selectedArea, setSelectedArea, Popup, scales, selector, statisticsKey }) {
  const { bbox, geojson } = geoData;
  const [hoverInfo, setHoverInfo] = useState({});
  const initialView = getInitialView(bbox);
  const getLineColor = d => {
    if (selectedArea == d?.properties?.id) {
      return [0,0,0,255];
    }
    return (hoverInfo?.object?.properties !== undefined &&
     d?.properties?.id === hoverInfo?.object?.properties?.id) ?
      [174, 30, 32] : [0, 0, 0, 60];
  };
  const layers = [
    new GeoJsonLayer({
      id: 'area-layer',
      data: geojson,
      pickable: true,
      stroked: true,
      filled: true,
      extruded: !!getElevation,
      getFillColor: getFillColor,
      getLineColor: getLineColor,
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 2,
      onHover: info => setHoverInfo(info),
      onClick: (setSelectedArea != null && ((info) => {
        setSelectedArea(info?.object?.properties?.id);
      })),
      getElevation,
      updateTriggers: {
        getFillColor: colorStateKey,
        getLineColor: hoverInfo?.object?.properties?.id,
        getElevation: statisticsKey
      }
    })
  ];
  const { t } = useTranslation();
  const popupValues = getTooltip(hoverInfo) ?? {};

  let elements = [];
  let title = null;
  if (scales != null) {
    title = t('transport-mode-share-km')
    elements = scales?.classes().map(val => (
      [scales(val).alpha(AREA_ALPHA).hex(), val]));
  }

  return (
    <div>
      <Layer>
        { selector }
        { elements && <ColorLegend title={title} elements={elements} /> }
        { hoverInfo.object && (
          <Popup
            x={hoverInfo.x}
            y={hoverInfo.y}
            weekSubset={weekSubset}
            {...popupValues}
          />
        )}
        </Layer>

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

function StatsPropertySelector ({ properties, selectedProperty, setSelectedProperty }) {
  const { t } = useTranslation();
  return <div style={{position: 'absolute', bottom: 20, right: 20}}>
    <Select
      closeOnSelect={true}
      ignoreCase={true}
      searchable={true}
      labelKey='description'
      valueKey='id'
      type={TYPE.search}
      value={selectedProperty.id != null ? [selectedProperty]: null}
      placeholder={t('choose-property')}
      onChange={params => setSelectedProperty(params.value[0]?.id)}
      options={properties}
    /></div>;
};

const AREA_ALPHA = 1;

export function TransportModeShareMap({ areaType,
                                        areaData,
                                        transportModes,
                                        selectedTransportMode,
                                        rangeLength,
                                        weekSubset,
                                        selectedArea,
                                        setSelectedArea,
                                        quantity,
                                        statisticsKey,
                                        setStatisticsKey
                                      }) {
  const geoData = useAreaTopo(areaType);
  if (!geoData) return <Spinner />;
  const modeId = selectedTransportMode.identifier;
  const modeById = new Map(transportModes.map(m => [m.identifier, m]));
  const areasById = new Map(areaType.areas.map(area => [parseInt(area.id), {...area}]))
  const statisticsBoundaries = geoData
    ?.statistics
    ?.params({statisticsKey})
    .filter((d, $) => d.property == $.statisticsKey)
    .filter(d => d.value !== -1)
    .rollup({min: aq.op.min('value'), max: aq.op.max('value')});

  let getFillColor = d => [0, 0, 0, 0];
  let getElevation;
  let colorStateKey = `${modeId}-nodata-${selectedArea}`;

  let scales = undefined;
  if (areaData) {
    const availableModes = areaData.columnNames((col) => modeById.has(col));
    areaData.objects().forEach((row) => {
      const area = areasById.get(row.areaId);
      if (!area) {
        if (row.areaId !== 'unknown') console.warn('Unknown area in input data', row);
        return;
      }
      area.data = row;
    });
    if (!availableModes.includes(modeId)) {
      //console.warn(`selected transport mode ${modeId} not found in data`);
    }
    else {
      const absoluteVals = areaData.array(modeId);
      absoluteVals.sort((a, b) => a - b);
      const minLength = absoluteVals[0];
      const maxLength = absoluteVals[absoluteVals.length - 1];
      const relativeVals = areaData.orderby(`${modeId}_rel`).array(`${modeId}_rel`);

      const limits = chroma.limits(relativeVals, 'q', 8);
      scales = chroma.scale([selectedTransportMode.colors.zero,
                             selectedTransportMode.colors.primary]).classes(limits);
    }

    getElevation = (d) => {
      const id = d.properties.id;
      const val = geoData?.statistics
        ?.params({id, statisticsKey})
        .filter((d, $) => (d.area === $.id && d.property == $.statisticsKey))
        .get('value', 0);
      if (val < 0) {
        return 0;
      }
      const [min, max] = [statisticsBoundaries.get('min', 0),
                          statisticsBoundaries.get('max', 0)];
      const result = 2000 * (val - min) / (max - min);
      return result;
    };
    getFillColor = (d) => {
      const id = d.properties.id;
      if (quantity === 'trips' && selectedArea == null) {
        return [0, 0, 0, 0]
      }
      if (id === selectedArea) {
        return [255, 255, 255, 255];
      }
      const area = areasById.get(id);
      if (area == null || !area.data || area.data[modeId] == null) return [0, 0, 0, 0];
      const val = area.data[modeId + '_rel'];
      const abs = area.data[modeId];
      if (quantity !== 'trips') {
        if (abs < 100) return [0, 0, 0, 0];
      }
      const color = scales(val).alpha(AREA_ALPHA);
      return [...color.rgb(), color.alpha()*255];
    },
    colorStateKey = `${modeId}-${selectedArea}`;
  }
  const getTooltip = ({object}) => {
    if (!object) return null;
    let { id, name, identifier } = object.properties;
    if (areaType.identifier !== 'tre:paavo') {
      identifier = null;
    }
    const area = areasById.get(id);
    if (!area || !area.data || area.data[modeId] == null) return null;
    const rel = area.data[modeId + '_rel'] * 100;
    const abs = area.data[modeId];
    const total = area.data[modeId];
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
    return { area: {name, identifier}, rel, transportMode: selectedTransportMode?.name, abs, syntheticModes, total, selectedArea: areasById.get(selectedArea) };
  };
  const selector = geoData?.statistics != null ? (
    <StatsPropertySelector
      properties={areaType.propertiesMeta}
      selectedProperty={{id: statisticsKey}}
      setSelectedProperty={setStatisticsKey} />) :
    null;

  return (
    <AreaMap
      selector={selector}
      statisticsKey={statisticsKey}
      scales={scales}
      geoData={geoData}
      getElevation={statisticsKey == null || geoData?.statistics == null ? null : getElevation}
      Popup={quantity === 'trips' ? AreaToAreaPopup : AreaPopup }
      getFillColor={getFillColor}
      colorStateKey={colorStateKey}
      getTooltip={getTooltip}
      selectedArea={selectedArea}
      setSelectedArea={setSelectedArea}
      weekSubset={weekSubset}
    />
  );
}
