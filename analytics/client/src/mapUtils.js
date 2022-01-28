export const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json';

export function getInitialView(bbox) {
  return {
    longitude: (bbox[0] + bbox[2]) / 2,
    latitude: (bbox[1] + bbox[3]) / 2 - 0.15,
    zoom: 11,
    pitch: 0,
    bearing: 0,
  };
}

export const getCursor = ({isHovering, isDragging}) => (
  isHovering ? 'pointer' :
  isDragging ? 'grabbing' :
   'grab'
)
