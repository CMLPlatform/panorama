// ECharts set-up shared by all charts. ECharts is loaded as a global script.
const echarts = window.echarts;

export const COLORS = {
  orange: "#FF9400",
  blue: "#24578C",
  lightBlue: "#2597C7",
  grey: "#CBD2D9",
};

// Colour-blind-friendly series palette that starts with the PANORAMA colours.
export const PALETTE = ["#24578C", "#FF9400", "#2597C7", "#7A9A01", "#B5446E", "#6C5B9E",
  "#00897B", "#C75B12", "#4F6D7A", "#9C7A3C", "#3C8DBC", "#D4A017"];

const BASE_OPTION = {
  color: PALETTE,
  textStyle: { fontFamily: "Open Sans, system-ui, sans-serif" },
  animationDuration: 400,
};

/** Create a chart in `element` that resizes with its container. */
export function createChart(element) {
  const chart = echarts.init(element, null, { renderer: "canvas" });
  new ResizeObserver(() => chart.resize()).observe(element);
  return {
    chart,
    render(option) {
      chart.setOption({ ...BASE_OPTION, ...option }, { notMerge: true });
    },
    clear() { chart.clear(); },
  };
}

export { echarts };
