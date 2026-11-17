// Use of each commodity (element) in the selected country: horizontal bars.
import { getJSON } from "../lib/api.js";
import { createChart, COLORS } from "../lib/chart.js";
import { formatNumber, formatTonnes } from "../lib/format.js";
import { addCheckbox, addSelect } from "../lib/ui.js";

const REST = "Rest of the elements";

export default async function setup(frame, ctx) {
  const update = () => refresh();
  const period = addSelect(frame.controls, { label: "Period", items: await ctx.lists.periods, onChange: update });
  const sort = addSelect(frame.controls, {
    label: "Sort",
    items: [{ id: "value", label: "By quantity" }, { id: "label", label: "By element" }],
    onChange: update,
  });
  const showRest = addCheckbox(frame.controls, { label: `Show "${REST}"`, onChange: update });
  const view = createChart(frame.canvas);

  async function refresh() {
    const path = `country_use/${ctx.main().id}/${period.value}`;
    const rows = await frame.run(path, () => getJSON(path));
    if (!rows) return;
    let data = rows.filter((r) => showRest.checked || r.element_label !== REST);
    if (!data.length) return frame.showMessage(`No data for ${ctx.main().label} in ${period.label}.`);
    data = [...data].sort(sort.value === "value"
      ? (a, b) => Number(b.use_value) - Number(a.use_value)
      : (a, b) => a.element_label.localeCompare(b.element_label));

    frame.canvas.style.height = `${Math.max(320, data.length * 30 + 80)}px`;
    view.chart.resize();
    view.render({
      grid: { left: 8, right: 32, top: 16, bottom: 40, containLabel: true },
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: formatTonnes },
      xAxis: { type: "value", name: "tonnes", nameLocation: "middle", nameGap: 28,
               axisLabel: { formatter: formatNumber } },
      yAxis: { type: "category", inverse: true, data: data.map((r) => r.element_label) },
      series: [{ type: "bar", name: "Use", itemStyle: { color: COLORS.blue },
                 data: data.map((r) => Number(r.use_value)) }],
    });
  }
  return update;
}
