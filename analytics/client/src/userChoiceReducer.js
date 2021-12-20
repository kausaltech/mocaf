export const initialUserChoiceState = {
  visualisation: 'choropleth-map',
  weekSubset: null,
  transportMode: 'car',
  areaType: 5,
  analyticsQuantity: 'lengths',
  dateRange: {
    bounds: [new Date(2021, 0, 1), new Date(2021, 11, 1)],
    range: [new Date(2021, 0, 1), new Date(2021, 11, 1)]
  }
}

export function userChoiceReducer(state, action) {
  if (action.type !== 'set' || action.payload === undefined || !action.key) {
    return state;
  }
  return Object.assign({}, state, {[action.key]: action.payload});
}
