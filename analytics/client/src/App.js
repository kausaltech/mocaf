import React, { useEffect, useState } from 'react';
import Papa from 'papaparse';
import 'mapbox-gl/dist/mapbox-gl.css';
import { gql, useQuery } from "@apollo/client";

import {Client as Styletron} from 'styletron-engine-atomic';
import {Provider as StyletronProvider} from 'styletron-react';
import {LightTheme, BaseProvider} from 'baseui';
import {Spinner} from 'baseui/spinner';

import Map from './Map';
import Controls from './Controls';


const engine = new Styletron();


const GET_AREAS = gql`
  query getAreas {
    analytics {
      areaTypes {
        id
        topojsonUrl
        dailyTripsUrl
        areas {
          id
          identifier
          name
        }
      }
    }
  }
`;


export function App() {
  const { loading, error, data } = useQuery(GET_AREAS);
  const [isLoaded, setIsLoaded] = useState(false);

  const areaType = data?.analytics.areaTypes[0];

  useEffect(() => {
    if (!areaType) return;

    Papa.parse(areaType.dailyTripsUrl, {
      download: true,
      header: true,
      complete: (results) => {
        console.log(results);
      },
    })
  }, [areaType]);

  if (error) {
    return <div>GraphQL error: {error}</div>
  }

  let main;
  if (!loading) {
    main = (
      <Map areaType={areaType} />
    );
  } else {
    main = <Spinner />;
  }

  return (
    <StyletronProvider value={engine}>
      <BaseProvider theme={LightTheme}>
        <div style={{display: 'flex', height: '100vh'}}>
          <div style={{width: '280px', height: '100vh'}}>
            <Controls />
          </div>
          <div style={{width: 'calc(100vw - 280px)', height: '100vh'}}>
            {main}
          </div>
        </div>
      </BaseProvider>
    </StyletronProvider>
  );
}
