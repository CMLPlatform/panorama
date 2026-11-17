// Europe map with countries shaded by value, value labels, and optional flow lines.
import { COLORS } from "./chart.js";
import { EUROPE_VIEW } from "./geo.js";
import { formatNumber, formatTonnes, escapeHtml } from "./format.js";

/**
 * @param view     result of createChart()
 * @param labels   label points by ISO3 code (from loadGeo)
 * @param values   Map of ISO3 code -> value in tonnes
 * @param selected ISO3 code of the selected country, or null
 * @param flows    [{from, to, value}] lines to draw, with ISO3 codes
 */
export function renderMap(view, { labels, values, selected = null, flows = [] }) {
  const max = Math.max(1, ...values.values());
  const name = (code) => labels[code]?.name ?? code;
  const points = [...values].filter(([code]) => labels[code]).map(([code, value]) => ({
    name: code, value: [...labels[code].coord, value],
  }));
  const lines = flows.filter((f) => labels[f.from] && labels[f.to]).map((f) => ({
    coords: [labels[f.from].coord, labels[f.to].coord], value: f.value, from: f.from, to: f.to,
  }));
  const maxFlow = Math.max(1, ...lines.map((l) => l.value));

  view.render({
    tooltip: {
      formatter: (p) => {
        if (p.seriesType === "lines") {
          return `${escapeHtml(name(p.data.from))} → ${escapeHtml(name(p.data.to))}<br>`
            + `<strong>${formatTonnes(p.data.value)}</strong>`;
        }
        const value = values.get(p.name);
        return `${escapeHtml(name(p.name))}<br><strong>${value === undefined ? "No data" : formatTonnes(value)}</strong>`;
      },
    },
    visualMap: {
      type: "continuous", min: 0, max, seriesIndex: 0, calculable: false,
      inRange: { color: ["#FFF1DB", COLORS.orange, "#B35F00"] },
      text: [formatNumber(max), "0"], left: 8, bottom: 8, itemHeight: 100,
    },
    geo: {
      map: "europe", roam: true, ...EUROPE_VIEW, scaleLimit: { min: 0.8, max: 12 },
      itemStyle: { areaColor: "#EEF1F4", borderColor: "#fff", borderWidth: 0.8 },
      emphasis: { label: { show: false }, itemStyle: { areaColor: COLORS.lightBlue } },
      select: { label: { show: false }, itemStyle: { areaColor: COLORS.lightBlue } },
      selectedMode: "single",
      regions: selected ? [{ name: selected, selected: true }] : [],
    },
    series: [
      { type: "map", geoIndex: 0, data: [...values].map(([code, value]) => ({ name: code, value })) },
      {
        type: "scatter", coordinateSystem: "geo", symbolSize: (v) => (v[0] === -25 ? 22 : 0),
        itemStyle: { color: COLORS.orange, opacity: 0.5 }, silent: true,
        label: { show: true, formatter: (p) => formatNumber(p.value[2]), fontSize: 10,
                 color: "#1F2933", textBorderColor: "#fff", textBorderWidth: 2 },
        data: points,
      },
      {
        type: "lines", coordinateSystem: "geo", zlevel: 1,
        symbol: ["none", "arrow"], symbolSize: 8,
        lineStyle: { color: COLORS.blue, curveness: 0.2, opacity: 0.8,
                     width: 1 },
        emphasis: { lineStyle: { width: 5 } },
        data: lines.map((l) => ({ ...l, lineStyle: { width: 1 + 5 * (l.value / maxFlow) } })),
      },
    ],
  });
}
