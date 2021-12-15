export const initialUserChoiceState = {
  visualisation: 'choropleth-map',
  weekSubset: 'workday',
  transportMode: 'car',
  areaType: 5,
  analyticsQuantity: 'lengths'
}

export function userChoiceReducer(state, action) {
  if (action.type !== 'set' || action.payload === undefined || !action.key) {
    return state;
  }
  return Object.assign({}, state, {[action.key]: action.payload});
}
