import React, { useEffect, useState } from 'react';
import * as topojson from 'topojson-client';
import {LineLayer, GeoJsonLayer} from '@deck.gl/layers';
import {StaticMap} from 'react-map-gl';
import DeckGL from '@deck.gl/react';
import { Spinner } from 'baseui/spinner';


export default function VizMap({ areaType }) {
  const [mapData, setMapData] = useState(null);

  console.log('map render');
  console.log(areaType);

  const processTopo = (topo) => {
    const areas = new Map(areaType.areas.map((area) => [area.id, area]));
    const { bbox } = topo;
    const geojson = topojson.feature(topo, topo.objects['-']);
    geojson.features = geojson.features.map((feat) => {
      const area = areas.get(feat.properties.id.toString());
      const out = {
        ...feat,
        properties: {
          ...feat.properties,
          name: area.name,
          identifier: area.identifier,
        },
      };
      return out;
    })
    return { bbox, geojson };
  };

  useEffect(() => {
    fetch(areaType.topojsonUrl)
      .then(res => res.json())
      .then(
        (res) => {
          setMapData(processTopo(res));
        },
        (error) => {
          console.error(error);
        }
      )
  }, []);

  if (!mapData) return <Spinner />;

  console.log('mapdata', mapData);
  const { bbox, geojson } = mapData;
  console.log(geojson);

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
      getFillColor: [160, 160, 180, 200],
      getLineColor: [0, 0, 0,200],
      lineWidthMinPixels: 1,
      lineWidthMaxPixels: 2,
    })
  ];
  const renderTooltip = ({object}) => {
    if (!object) return;
    const { name, identifier } = object.properties;
    return `${name} (${identifier})`;
  };
  return (
    <div><DeckGL
      initialViewState={initialView}
      controller={true}
      layers={layers}
      getTooltip={renderTooltip}
      style={{
        left: '280px',
        width: 'calc(100vw - 280px)'
      }}
    >
      <StaticMap mapboxApiAccessToken={MAPBOX_ACCESS_TOKEN} />
    </DeckGL></div>
  );
}
