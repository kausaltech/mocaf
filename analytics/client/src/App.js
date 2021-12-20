import React, { useReducer, useEffect } from 'react';
import { gql, useQuery } from "@apollo/client";
import { format, addMonths } from 'date-fns';

import {Client as Styletron} from 'styletron-engine-atomic';
import {Provider as StyletronProvider} from 'styletron-react';
import {LightTheme, BaseProvider} from 'baseui';
import {Layer} from 'baseui/layer';
import {StyledSpinnerNext as Spinner} from 'baseui/spinner';

import i18n from './common/i18n';
import { TransportModeShareMap } from './Map';
import Controls from './Controls';
import { useAnalyticsData } from './data';
import {userChoiceReducer, initialUserChoiceState} from './userChoiceReducer';
import { OriginDestinationMatrix, TransportModesPlot } from './Plots';


const engine = new Styletron();


const GET_AREAS = gql`
  query getAreas {
    analytics {
      areaTypes {
        id
        topojsonUrl
        dailyTripsUrl
        dailyLengthsUrl
        areas {
          id
          identifier
          name
        }
      }
    }
    transportModes {
      id
      identifier
      name
    }
  }
`;

export function MocafAnalytics({ transportModes, areaTypes }) {
  // FIXME: Generate initialUserChoiceState based on component props.
  // Alternatively, use lazy init: https://reactjs.org/docs/hooks-reference.html#lazy-initialization
  const [userChoiceState, dispatch] = useReducer(userChoiceReducer, initialUserChoiceState);
  const areaType = areaTypes.filter((areaType) => areaType.id == userChoiceState.areaType)[0];
  const selectedTransportMode = transportModes.filter((mode) => mode.identifier === userChoiceState.transportMode)[0];
  const areaData = useAnalyticsData({
    type: userChoiceState.analyticsQuantity,
    areaTypeId: areaType.id,
    weekend: userChoiceState.weekSubset,
    startDate: format(userChoiceState.dateRange.range[0], 'yyyy-MM-dd'),
    endDate: format(addMonths(userChoiceState.dateRange.range[1], 1), 'yyyy-MM-dd'),
  });

  let visComponent;
  if (userChoiceState.visualisation === 'choropleth-map') {
    if (userChoiceState.analyticsQuantity === 'lengths') {
      visComponent = (
        <TransportModeShareMap
          areaType={areaType}
          areaData={areaData}
          selectedTransportMode={selectedTransportMode}
          transportModes={transportModes} />
      );
    }
  } else if (userChoiceState.visualisation === 'table') {
    if (userChoiceState.analyticsQuantity === 'lengths') {
      visComponent = (
        <div style={{ paddingTop: '180px' }}>

        <TransportModesPlot
          areaType={areaType}
          areaData={areaData}
          transportModes={transportModes}
        />
        </div>
      );
    } else {
      visComponent = <OriginDestinationMatrix transportModes={transportModes} areaType={areaType} areaData={areaData} mode={selectedTransportMode} />
    }
  }

  return (
    <div style={{display: 'flex', height: '100vh'}}>
      <Layer>
        <Controls userChoices={[userChoiceState, dispatch]}
                  dynamicOptions={{transportModes: transportModes.filter((m) => m.identifier !== 'still')}}
        />
      </Layer>
    <div style={{width: 'calc(100vw - 280px)', height: '100vh'}}>
      {visComponent}
    </div>
  </div>
)
}

export function App() {
  const { loading, error, data } = useQuery(GET_AREAS);

  let mainComponent;
  if (error) {
    mainComponent = <div>GraphQL error: {error}</div>;
  } else if (loading) {
    mainComponent = <Spinner />;
  } else {
    mainComponent = <MocafAnalytics transportModes={data.transportModes} areaTypes={data.analytics.areaTypes} />
  }
  return (
    <StyletronProvider value={engine}>
      <BaseProvider theme={LightTheme}>
        {mainComponent}
      </BaseProvider>
    </StyletronProvider>
  );
}
