// MapViewUpdater.jsx
import { useEffect } from "react";
import { useMap } from "react-leaflet";

/**
 * Update map view when center or zoom changes
 */
export default function MapViewUpdater({ center, zoom }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !center || !zoom) return;

    map.flyTo(center, zoom, {
      animate: true,
      duration: 0.8,
    });
  }, [center, zoom, map]);

  return null;
}
