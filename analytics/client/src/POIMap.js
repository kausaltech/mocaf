import React, { useState } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { StaticMap } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import lodash from 'lodash';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import { Layer } from 'baseui/layer';
import { useTranslation } from 'react-i18next';
import * as aq from 'arquero';

import { formatFloat } from './utils';
import { MAP_STYLE, getInitialView, getCursor } from './mapUtils';
import { Popup } from './Popup.js';
import { orderedTransportModeIdentifiers } from './transportModes';
import { useAreaTopo, usePoiGeojson } from './data';

function SmallBarChartElement({spec, children, verticalOffset, fontSize, padding}) {
  fontSize = fontSize ?? 12;
  let width = null;
  if (spec.x != null && !isNaN(spec.x)) {
    width = spec.x;
  }
  return <div style={{
                position: 'absolute',
                top: 5 + verticalOffset,
                left: spec.cumulativeX,
                width,
                height: 15,
                backgroundColor: spec.color,
                fontSize,
                paddingTop: padding}}>
           {children}
           </div>
}

function SmallBarChartLegend({spec}) {
  spec.color = null;
  return <SmallBarChartElement spec={spec} verticalOffset={0} fontSize={10}>
           <span style={{paddingLeft: 2, backgroundColor: 'white'}}>{ spec.legend }</span>
         </SmallBarChartElement>
}

function SmallBarChart({rowName, specs, leftBorder}) {
  specs[0].cumulativeX = 0;
  for (let i = 0; i < specs.length - 1; i++) {
    specs[i+1].cumulativeX = 1 + specs[i].x + specs[i].cumulativeX;
  }
  let legendRow;
  if (specs[0].legend != null) {
    const rowNameCell = rowName != null ? <td/> : null;
    legendRow = <tr>
                  { rowNameCell }
                  <td style={{position: 'relative', width: '100px', borderLeft: leftBorder ? '1px solid black' : null}}>
      {specs.map((spec, index) => <SmallBarChartLegend key={index} spec={spec} />)}
    </td>
    </tr>
  }
  const rowNameCell = rowName != null ? <td style={{verticalAlign: 'top', paddingRight: 4, paddingTop: 5, textAlign: 'right', fontSize: 14, height: 15}}>{rowName}</td> : null;
  return <>
    <tr>
      { rowNameCell  }
      <td style={{position: 'relative', width: '100px', borderLeft: leftBorder ? '1px solid black' : null}}>
        {specs.map((spec, index) => (
          <SmallBarChartElement key={index} spec={spec} verticalOffset={0} padding={spec.value != null ? 2 : null}>
            { spec.value != null && <span style={{color: spec.value === 0 ? 'black' : 'white', paddingLeft: 4}}>{spec.value}</span> }
          </SmallBarChartElement>
        ))}
      </td>
    </tr>
    { legendRow }
  </>;
}


function POICounterPartModeBar({row, inbound, scale, transportModes, orderedModeIds}) {
  const currentModes = Object.keys(row.breakdown);
  orderedModeIds = orderedModeIds.filter(m => currentModes.includes(m));
  const specs = orderedModeIds.map((k, index) => ({
    color: transportModes.get(k),
    x: Math.round((100*row.breakdown[k]/scale)) - 1,
  }))
  return <SmallBarChart rowName={row.name} specs={specs} leftBorder={true} />;
}

function POITotalTripsBar({inbound, outbound}) {
  const { t } = useTranslation();
  const total = inbound + outbound;
  if (total === 0) {
    return <div>{t('no-data')}</div>
    return null;
  }
  const elements = [
    { color: '#335595', value: inbound,  legend: t('inbound')},
    { color: '#8ca1c5', value: outbound, legend: t('outbound')}
  ];
  const specs = elements.map(el => (Object.assign({}, el, {
    x: Math.max(Math.round(((200*el.value)/total)) - 1, 0)
  }))).sort((a,b) => b.value - a.value);
  return <table style={{height: 40}}>
           <caption style={{textAlign: 'start'}}>
             {total} {t('trips-total')}
           </caption>
           <tbody>
             <SmallBarChart rowName={null} specs={specs} leftBorder={false} />
           </tbody>
         </table>;
}


function POICounterPartsTable({inbound, group, transportModes, orderedModeIds}) {
  const { t } = useTranslation();
  const scale = group[0].total_trips;
  return <table cellSpacing={0} key={inbound ? 'inbound' : 'outbound'}
                 style={{marginRight: '10px'}}>
            <caption style={{textAlign: 'start', fontWeight: 'bold', fontSize: 18}}>
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
          </table>;
}

function AverageTripLengthTable({rangeLength, tripLengths}) {
  const { t } = useTranslation();
  const scale = Math.max(...Object.values(tripLengths));
  return <table cellSpacing={0} style={{marginBottom: 20}}>
           <caption style={{fontSize: 14, paddingTop: 4, paddingBottom: 4}}>
             { t('average-length') }
           </caption>
           <tbody>
             {
               ['inbound', 'outbound'].map ((key) => (
                 <tr key={`average-trip-length-${key}`}>
                   <td style={{paddingRight: 2, fontSize: 14, textAlign: 'right', verticalAlign: 'top'}}>
                     { t(key) }
                   </td>
                   <td style={{position: 'relative', width: 120}}>
                     <SmallBarChartElement
                       verticalOffset={-5}
                       spec={{
                         cumulativeX: 0,
                         x: 100*tripLengths[key]/scale, color: '#335595'
                       }}>
                      <span style={{whiteSpace: 'nowrap',
                                    paddingTop: 4,
                                    paddingLeft: 4,
                                    color: 'white',
                                    mixBlendMode: 'difference'}}>
                      {isNaN(tripLengths[key]) ? 0 : formatFloat(tripLengths[key])}&nbsp;km</span>
                       </SmallBarChartElement>
                   </td>
                 </tr>
               ))
             }
           </tbody>
         </table>;
}

const getCircularReplacer = () => {
  const seen = new WeakSet();
  return (key, value) => {
    if (typeof value === "object" && value !== null) {
      if (seen.has(value)) {
        return;
      }
      seen.add(value);
    }
    return value;
  };
};

export default function POIMap({ poiType, areaType, areaData, transportModes,
                         selectedTransportMode, weekSubset, rangeLength }) {
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
  let topFiveAreas, totalTrips, totalLengths;
  if (popupData?.poiId) {
    const currentPoiData = areaData
      .params({poiId: popupData.poiId})
      .filter((d, $) => d.poiId === $.poiId)

    topFiveAreas = currentPoiData
      .select('areaId', 'isInbound', 'trips', 'poiId', 'mode')
      .groupby('isInbound', 'areaId')
      .rollup({total_trips: aq.op.sum('trips'),
               breakdown: aq.op.object_agg('mode', 'trips')})
      .ungroup()
      .orderby(aq.desc('total_trips'))
      .groupby('isInbound')
      .slice(0, 5)
      .lookup(areaTable, ['areaId', 'areaId'], 'name', 'identifier');

    totalTrips = currentPoiData
      .select('isInbound', 'trips', 'length')
      .groupby('isInbound')
      .rollup({total_trips: aq.op.sum('trips'),
               total_length: aq.op.sum('length')})
      .objects();
  }
  const getFillColor = (d) => {
    if (d.properties.id === hoverInfo?.object?.properties?.id) {
      return [174,30,32,255];
    }
    return [0,65,125,255];
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
      getLineColor: [255, 255, 255, 255],
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 3,
      updateTriggers: {
        getFillColor: [
          hoverInfo
            ? hoverInfo?.object?.properties?.id
            : null
        ]
      },
      onHover: (info) => setHoverInfo(info)
    }),

  ];
  const groups = topFiveAreas?.groupby('isInbound')
        .objects({grouped: true})
  const popupTitle = <strong>{popupData?.poiName}</strong>;

  let popupContents = [];
  if (totalTrips) {
    const [[inboundTripProperties], [outboundTripProperties]] = lodash.partition(totalTrips, r => r.isInbound);
    const inboundTrips = Math.round(inboundTripProperties?.total_trips ?? 0);
    const outboundTrips = Math.round(outboundTripProperties?.total_trips ?? 0);
    const allTrips = Math.round(inboundTrips + outboundTrips);
    const inboundLength = Math.round(inboundTripProperties?.total_length ?? 0) / inboundTrips;
    const outboundLength = Math.round(outboundTripProperties?.total_length ?? 0) / outboundTrips;
    popupContents = groups ? [
      <POITotalTripsBar key="poi-total-trips" inbound={inboundTrips} outbound={outboundTrips} />,
      <AverageTripLengthTable key="poi-average-trip-length" rangeLength={rangeLength} tripLengths={{
                                inbound: inboundLength,
                                outbound: outboundLength }}/>
    ] : null;
    if (popupContents && groups != null) {
      popupContents = popupContents.concat([true, false].map(inbound => {
        const group = groups.get(inbound);
        if (group == null) {
          return;
        }
        return <POICounterPartsTable
                 inbound={inbound}
                 group={group}
                 key={`table-${inbound}`}
                 transportModes={new Map(transportModes.map(m => [m.identifier, m.colors.primary]))}
                 orderedModeIds={orderedTransportModeIdentifiers(transportModes, 'car')}
               />;
      }));
    }
  }
  return (
    <div>
      <Layer>
        { popupContents.length > 0 &&
          <Popup weekSubset={weekSubset}
                 maxWidth={560}
                 x={hoverInfo.x}
                 y={hoverInfo.y}
                 title={popupTitle}>
            <div style={{
                   display: 'grid',
                   gridTemplateColumns: '1fr 1fr',
                   gap: 4
                 }}>
              {popupContents}
            </div>
          </Popup>}
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
