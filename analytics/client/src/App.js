import React, { useReducer, useEffect } from 'react';
import { gql, useQuery } from "@apollo/client";
import { format, addDays, differenceInDays } from 'date-fns';

import {Client as Styletron} from 'styletron-engine-atomic';
import {Provider as StyletronProvider} from 'styletron-react';
import {LightTheme, BaseProvider} from 'baseui';
import {Layer} from 'baseui/layer';
import {StyledSpinnerNext as Spinner} from 'baseui/spinner';
import { useTranslation } from 'react-i18next';

import i18n from './common/i18n';
import { TransportModeShareMap } from './Map';
import POIMap from './POIMap';
import Controls from './Controls';
import VisualisationGuideModal from './VisualisationGuideModal';
import { useAnalyticsData } from './data';
import {userChoiceReducer, initializeUserChoiceState} from './userChoiceReducer';
import { AreaBarChart, TransportModesPlot } from './Plots';
import preprocessTransportModes from './transportModes';


// Use the symbol to prevent esbuild from tree-shaking it out
if (!i18n.hasLoadedNamespace()) {
  throw new Error('i18n has not loaded')
}

const engine = new Styletron();


const GET_AREAS = gql`
  query getAreas($language: String!) @locale(lang:$language) {
    analytics {
      areaTypes {
        id
        topojsonUrl
        geojsonUrl
        identifier
        name
        dailyTripsDateRange
        dailyPoiTripsDateRange
        dailyLengthsDateRange
        isPoi
        areas {
          id
          identifier
          name
        }
      }
      visualisationGuides {
        id
        title
        body
      }
    }
    transportModes {
      id
      identifier
      name
    }
  }
`;

export function MocafAnalytics({ transportModes, areaTypes, visualisationGuideContents }) {
  const administrativeAreaTypes = areaTypes.filter(areaType => !areaType.isPoi);
  const [userChoiceState, dispatch] = useReducer(
    userChoiceReducer, ['tre:tilastoalue', areaTypes], initializeUserChoiceState);
  const poiAreaTypes = areaTypes.filter(areaType => areaType.isPoi);
  const poiType = poiAreaTypes[0];
  const areaType = administrativeAreaTypes.filter((areaType) => areaType.identifier == userChoiceState.areaType)[0];
  const selectedTransportMode = transportModes.filter((mode) => mode.identifier === userChoiceState.transportMode)[0];
  const start = userChoiceState.dateRange.range[0];
  const end = addDays(userChoiceState.dateRange.range[1], 1)
  const rangeLength = differenceInDays(end, start);
  const areaData = useAnalyticsData({
    type: userChoiceState.analyticsQuantity,
    areaTypeId: areaType.id,
    poiTypeId: poiType.id,
    selectedArea: userChoiceState.visualisationState.trips.selectedArea,
    weekend: userChoiceState.weekSubset,
    startDate: format(start, 'yyyy-MM-dd'),
    endDate: format(end, 'yyyy-MM-dd'),
    transportModes,
  });

  const selectedArea = userChoiceState.visualisationState.trips.selectedArea;
  const setSelectedArea = (area) => {
    dispatch({
      type: 'set',
      key: ['visualisationState', 'trips', 'selectedArea'],
      payload: area
    })};

  const weekSubset = userChoiceState.weekSubset;
  let visComponent;
  if (userChoiceState.visualisation === 'choropleth-map') {
    switch (userChoiceState.analyticsQuantity) {
    case 'lengths':
      visComponent = (
        <TransportModeShareMap
          areaType={areaType}
          areaData={areaData}
          selectedTransportMode={selectedTransportMode}
          transportModes={transportModes}
          rangeLength={rangeLength}
          weekSubset={weekSubset}
        />
      );
      break;
    case 'poi_trips':
      visComponent = (
        <POIMap
          poiType={poiType}
          areaType={areaType}
          areaData={areaData}
          quantity={userChoiceState.analyticsQuantity}
          weekSubset={weekSubset}
          rangeLength={rangeLength}
          selectedTransportMode={selectedTransportMode}
          transportModes={transportModes} />
      );
      break;
    case 'trips':
      visComponent = (
        <TransportModeShareMap
          areaType={areaType}
          areaData={areaData}
          quantity={userChoiceState.analyticsQuantity}
          selectedTransportMode={selectedTransportMode}
          transportModes={transportModes}
          rangeLength={rangeLength}
          weekSubset={weekSubset}
          setSelectedArea={setSelectedArea}
          selectedArea={selectedArea}
        />
      );
      break;
    }
  } else if (userChoiceState.visualisation === 'table') {
    switch (userChoiceState.analyticsQuantity) {
    case 'lengths':
      visComponent = (
        <TransportModesPlot
          areaType={areaType}
          areaData={areaData}
          weekSubset={weekSubset}
          selectedTransportMode={selectedTransportMode}
          transportModes={transportModes}
          rangeLength={rangeLength}
        />
      );
      break;
    case 'trips':
      visComponent = (
        <AreaBarChart
          transportModes={transportModes}
          areaType={areaType}
          areaData={areaData}
          selectedArea={selectedArea}
          setSelectedArea={setSelectedArea}
        />);
      break;
    }
  }

  return (
    <div style={{display: 'flex', height: '100vh'}}>
      <Layer>
        <Controls userChoices={[userChoiceState, dispatch]}
                  dynamicOptions={{transportModes, areaTypes: administrativeAreaTypes}}
        />
      </Layer>
      <VisualisationGuideModal
        contents={visualisationGuideContents}
        visible={userChoiceState.modalVisible}
        dispatch={dispatch} />
      <div style={{width: '100vw', height: '100vh', paddingTop: '180px'}}>
        {visComponent}
      </div>
    </div>
  )
}

export function App() {
  const { t, i18n } = useTranslation();
  const { loading, error, data } = useQuery(GET_AREAS, {variables: {language: i18n.language}});

  let mainComponent;
  if (error) {
    mainComponent = <div>{t('error-graphql')}: {error}</div>;
  } else if (loading) {
    mainComponent = <Spinner />;
  } else {
    mainComponent = <MocafAnalytics
                      transportModes={preprocessTransportModes(data.transportModes, i18n.language)}
                      areaTypes={data.analytics.areaTypes}
                      visualisationGuideContents={data.analytics.visualisationGuides}/>
  }
  return (
    <StyletronProvider value={engine}>
      <BaseProvider theme={LightTheme}>
        {mainComponent}
      </BaseProvider>
    </StyletronProvider>
  );
}
