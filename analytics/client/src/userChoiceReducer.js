import { parseISO, addMonths, max, min } from 'date-fns';
import { syntheticModes } from './transportModes';

const syntheticModeNames = syntheticModes.map(m => m.identifier);

const defaultDateBounds = [
  new Date(2021, 6, 1), new Date(2021, 10, 1)]

export function initializeUserChoiceState ([initialAreaType, areaTypes]) {
  const defaults = {
    visualisation: 'choropleth-map',
    weekSubset: null,
    transportMode: 'walk',
    areaType: initialAreaType,
    analyticsQuantity: 'lengths',
    areaTypes
  };
  defaults.dateRange = areaTypeDateRange(
    defaults.analyticsQuantity,
    defaults.areaType,
    areaTypes,
    {range: null, bounds: null});
  return defaults;
}

function restrictDateRange({range, bounds}) {
  if (range === null) {
    range = [...bounds]
  }
  range[0] = max([range[0], bounds[0]]);
  range[1] = min([range[1], bounds[1]]);
  return { bounds, range };
}

function areaTypeDateRange(analyticsQuantity, areaTypeIdentifier, areaTypes, dateRange) {
  const { dailyLengthsDateRange, dailyTripsDateRange } = areaTypes.find(a => a.identifier === areaTypeIdentifier);
  const rangeStrings = (analyticsQuantity === 'lengths' ? dailyLengthsDateRange : dailyTripsDateRange);
  let bounds;
  if (rangeStrings === null) {
    bounds = defaultDateBounds;
  }
  else {
    bounds = rangeStrings.map(parseISO);
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
    dependentState.transportMode = initialUserChoiceState.transportMode;
  }
  if (action.key === 'areaType' || action.key === 'analyticsQuantity') {
    dependentState.dateRange = areaTypeDateRange(
      state.analyticsQuantity,
      action.payload,
      state.areaTypes,
      state.dateRange);
  }
  if (action.key == 'dateRange') {
    action.payload = restrictDateRange(action.payload);
  }
  return {
    ...state,
    ...dependentState,
    ...{[action.key]: action.payload}};
}
