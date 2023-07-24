import { parseISO, addMonths, max, min } from 'date-fns';
import { syntheticModes } from './transportModes';

const syntheticModeNames = syntheticModes.map(m => m.identifier);

const defaultDateBounds = [
  new Date(2023, 6, 1), new Date(2023, 10, 1)]

const DEFAULT_TRANSPORTMODE = 'walk';

export function initializeUserChoiceState ([initialAreaType, areaTypes]) {
  const defaults = {
    visualisation: 'choropleth-map',
    weekSubset: null,
    transportMode: DEFAULT_TRANSPORTMODE,
    areaType: initialAreaType,
    analyticsQuantity: 'lengths',
    areaTypes,
    modalVisible: false,
    visualisationState: { trips: { selectedArea: null } },
    statisticsKey: null,
  };
  defaults.dateRange = areaTypeDateRange(
    defaults.analyticsQuantity,
    defaults.areaType,
    areaTypes,
    {range: null, bounds: null});
  return defaults;
}

function restrictDateRange({range, bounds}) {
  const ifBounds = bounds || defaultDateBounds;
  if (range === null) {
    range = [...ifBounds]
  }
  range[0] = max([range[0], ifBounds[0]]);
  range[1] = min([range[1], ifBounds[1]]);
  return { bounds, range };
}

function areaTypeDateRange(analyticsQuantity, areaTypeIdentifier, areaTypes, dateRange) {
  if (analyticsQuantity === 'poi_trips') {
    areaTypeIdentifier = 'tre:poi';
  }
  areaTypes.find(
    a => a.identifier === areaTypeIdentifier);
  let rangeStrings;
  if (analyticsQuantity === 'lengths') {
    rangeStrings = areaTypes?.dailyLengthsDateRange;
  }
  if (analyticsQuantity === 'trips') {
    rangeStrings = areaTypes?.dailyTripsDateRange;
  }
  if (analyticsQuantity === 'poi_trips') {
    rangeStrings = areaTypes?.dailyPoiTripsDateRange;
  }
  let bounds;
  if (rangeStrings === null) {
    bounds = defaultDateBounds;
  }
  else {
    bounds = rangeStrings?.map(parseISO);
  }
  return restrictDateRange(Object.assign({}, dateRange, {bounds}));

}

export function userChoiceReducer (state, action) {
  if (action.type !== 'set' || action.payload === undefined || !action.key) {
    return state;
  }
  let dependentState = {};
  if (action.key === 'visualisation' && action.payload === 'table' &&
      syntheticModeNames.includes(state.transportMode)) {
    dependentState.transportMode = DEFAULT_TRANSPORTMODE;
  }
  if (action.key === 'areaType') {
    dependentState.dateRange = areaTypeDateRange(
      state.analyticsQuantity,
      action.payload,
      state.areaTypes,
      state.dateRange);
    dependentState.visualisationState = { trips: { selectedArea: null } };
  }
  if (action.key === 'analyticsQuantity') {
    dependentState.dateRange = areaTypeDateRange(
      action.payload,
      state.areaType,
      state.areaTypes,
      state.dateRange);
  }
  if (action.key === 'analyticsQuantity' && action.payload === 'poi_trips') {
    dependentState.visualisation = 'choropleth-map';
  }
  if (action.key === 'visualisation' && state.analyticsQuantity === 'poi_trips') {
    action.payload = 'choropleth-map';
  }
  if (action.key == 'dateRange') {
    action.payload = restrictDateRange(action.payload);
  }
  if (action.key instanceof Array && action.key[0] === 'visualisationState') {
    let target = state;
    for (key of action.key.slice(0, -1)) target = target[key];
    target[action.key.at(-1)] = action.payload;
    return Object.assign({}, state);
  }
  else {
    return {
      ...state,
      ...dependentState,
      ...{[action.key]: action.payload}};
  }
}
