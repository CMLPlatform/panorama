// Map data: European country borders (Eurostat GISCO) and label points.
import { echarts } from "./chart.js";

let ready = null;

/** Register the "europe" map once and return the label points by ISO3 code. */
export function loadGeo() {
  if (!ready) {
    ready = Promise.all([
      fetch("/static/geo/europe.json").then((r) => r.json()),
      fetch("/static/geo/labels.json").then((r) => r.json()),
    ]).then(([europe, labels]) => {
      echarts.registerMap("europe", europe);
      return labels;
    });
  }
  return ready;
}

// Area shown when a map opens: Europe, plus the Atlantic for the "Rest of the World"
// marker. Without this box, Russia stretches the map to 180° east.
// boundingCoords: [[west, north], [east, south]].
export const EUROPE_VIEW = { boundingCoords: [[-30, 71], [42, 34]] };
