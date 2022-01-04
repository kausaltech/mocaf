import { syntheticModes } from './transportModes';

const syntheticModeNames = syntheticModes.map(m => m.identifier);

export const initialUserChoiceState = {
  visualisation: 'choropleth-map',
  weekSubset: null,
  transportMode: 'walk',
  areaType: 'tre:tilastoalue',
  analyticsQuantity: 'lengths',
  dateRange: {
    bounds: [new Date(2021, 5, 1), new Date(2021, 11, 1)],
    range: [new Date(2021, 5, 1), new Date(2021, 11, 1)]
  }
}

export function userChoiceReducer(state, action) {
  if (action.type !== 'set' || action.payload === undefined || !action.key) {
    return state;
  }
  let dependentState = {};
  if (action.key === 'visualisation' && action.payload === 'table' &&
      syntheticModeNames.includes(state.transportMode)) {
    dependentState.transportMode = initialUserChoiceState.transportMode;
  }
  return Object.assign({}, state, dependentState, {[action.key]: action.payload});
}
