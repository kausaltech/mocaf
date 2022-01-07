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
    null);
  return defaults;
}

function areaTypeDateRange(analyticsQuantity, areaTypeIdentifier, areaTypes, currentRange) {
  const { dailyLengthsDateRange, dailyTripsDateRange } = areaTypes.find(a => a.identifier === areaTypeIdentifier);
  const rangeStrings = (analyticsQuantity === 'lengths' ? dailyLengthsDateRange : dailyTripsDateRange);
  let bounds;
  if (rangeStrings === null) {
    bounds = defaultDateBounds;
  }
  else {
    bounds = rangeStrings.map(parseISO);
  }
  bounds.forEach((d) => d.setDate(1));
  if (currentRange === null) {
    currentRange = [...bounds]
  }
  currentRange[0] = max([currentRange[0], bounds[0]]);
  currentRange[1] = min([currentRange[1], bounds[1]]);
  return {
    bounds,
    range: currentRange };
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
  if (action.key === 'areaType') {
    dependentState.dateRange = areaTypeDateRange(
      state.analyticsQuantity,
      action.payload,
      state.areaTypes,
      state.dateRange.range);
  }
  return {
    ...state,
    ...dependentState,
    ...{[action.key]: action.payload}};
}
