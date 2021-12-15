export const initialUserChoiceState = {
  visualisation: 'choropleth-map',
  weekSubset: null,
  transportMode: 'car',
  areaType: 5,
  analyticsQuantity: 'lengths',
  dateRange: {
    bounds: [new Date(2020, 11, 15), new Date(2022, 0, 15)],
    range: [new Date(2021, 4, 1), new Date(2021, 9, 31)]
  }
}

export function userChoiceReducer(state, action) {
  if (action.type !== 'set' || action.payload === undefined || !action.key) {
    return state;
  }
  return Object.assign({}, state, {[action.key]: action.payload});
}
