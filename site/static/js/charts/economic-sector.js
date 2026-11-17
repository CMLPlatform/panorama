// Use of an element by economic sector (ISIC) and contributor: stacked bars.
import { getJSON } from "../lib/api.js";
import { createChart } from "../lib/chart.js";
import { formatNumber, formatTonnes } from "../lib/format.js";
import { addSelect } from "../lib/ui.js";

export default async function setup(frame, ctx) {
  const update = () => refresh();
  const area = addSelect(frame.controls, { label: "Geographic area", items: await ctx.lists.areas, onChange: update });
  const period = addSelect(frame.controls, { label: "Period", items: await ctx.lists.periods, onChange: update });
  const view = createChart(frame.canvas);

  async function refresh() {
    const path = `economic_sector/${ctx.main().id}/${area.value}/${period.value}`;
    const rows = await frame.run(path, () => getJSON(path));
    if (!rows) return;
    if (!rows.length) return frame.showMessage(`No data for ${ctx.main().label} in ${area.label}.`);

    const sectors = rows.map((r) => r.isic);
    const contributors = [...new Set(rows.flatMap((r) => Object.keys(r).filter((k) => k !== "isic")))];
    frame.canvas.style.height = `${Math.max(360, sectors.length * 40 + 140)}px`;
    view.chart.resize();
    view.render({
      legend: { type: "scroll", bottom: 0 },
      grid: { left: 8, right: 32, top: 16, bottom: 56, containLabel: true },
      tooltip: { trigger: "item", valueFormatter: formatTonnes },
      xAxis: { type: "value", axisLabel: { formatter: formatNumber } },
      yAxis: { type: "category", inverse: true, data: sectors,
               axisLabel: { width: 160, overflow: "truncate" } },
      series: contributors.map((name) => ({
        type: "bar",
        name,
        stack: "total",
        emphasis: { focus: "series" },
        data: rows.map((r) => (r[name] === undefined ? null : Number(r[name]))),
      })),
    });
  }
  return update;
}
