export const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

export function getInitialView(bbox) {
  return {
    longitude: 23.8,
    latitude: 61.5,
    zoom: 11,
    pitch: 0,
    bearing: 0
  };
}

export const getCursor = ({isHovering, isDragging}) => (
  isHovering ? 'pointer' :
  isDragging ? 'grabbing' :
   'grab'
)
