import React, { useState } from 'react';
import { GeoJsonLayer } from '@deck.gl/layers';
import { StaticMap } from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { StyledSpinnerNext as Spinner } from 'baseui/spinner';
import { Layer } from 'baseui/layer';
import { useTranslation } from 'react-i18next';
import * as aq from 'arquero';

import { MAP_STYLE, getInitialView, getCursor } from './mapUtils';
import { Popup } from './Popup.js';
import { orderedTransportModeIdentifiers } from './transportModes';
import { useAreaTopo, usePoiGeojson } from './data';

function SmallBarChartElement({spec, children, verticalOffset, fontSize, padding}) {
  fontSize = fontSize ?? 12;
  return <div style={{
                position: 'absolute',
                top: 5 + verticalOffset,
                left: spec.cumulativeX,
                width: spec.x,
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
    legendRow = <tr> { rowName && <td/> }
                  <td style={{position: 'relative', width: '100px', borderLeft: leftBorder ? '1px solid black' : null}}>
      {specs.map((spec, index) => <SmallBarChartLegend key={index} spec={spec} />)}
    </td>
    </tr>
  }
  return <>
    <tr>
      { rowName && <td style={{paddingRight: '4px', textAlign: 'right'}}>{rowName}</td> }
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
  const elements = [
    { color: '#335595', value: inbound,  legend: t('inbound')},
    { color: '#8ca1c5', value: outbound, legend: t('outbound')}
  ];
  const specs = elements.map(el => (Object.assign({}, el, {
    x: Math.max(Math.round(((200*el.value)/total)) - 1, 0)
  }))).sort((a,b) => b.value - a.value);
  console.log(specs);
  return <><div>{total} {t('trips-total')}</div>
           <table style={{clear: 'both', height: 40}}>
             <tbody>
               <SmallBarChart rowName={null} specs={specs} leftBorder={false} />
             </tbody>
           </table></>;
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
  let topFiveAreas, totalTrips;
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
      .select('isInbound', 'trips')
      .groupby('isInbound')
      .rollup({total_trips: aq.op.sum('trips')})
      .pivot('isInbound', 'total_trips')
      .object(0);
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
      onHover: (info) => setHoverInfo(info)
    }),

  ];
  const groups = topFiveAreas?.groupby('isInbound')
        .objects({grouped: true})
  const popupTitle = <strong>{popupData?.poiName}</strong>;

  let popupContents = [];
  if (totalTrips) {
    const inboundTrips = Math.round(totalTrips[true] ?? 0);
    const outboundTrips = Math.round(totalTrips[false] ?? 0);
    const allTrips = Math.round(inboundTrips + outboundTrips);
    popupContents = groups ? [
      <POITotalTripsBar inbound={inboundTrips} outbound={outboundTrips} />
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
                 children={popupContents}
                 title={popupTitle} />}
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
