// Element composition of a product: half doughnut, in percent.
import { getJSON } from "../lib/api.js";
import { createChart } from "../lib/chart.js";
import { escapeHtml } from "../lib/format.js";
import { addSelect } from "../lib/ui.js";

const MODES = [
  { id: "make", label: "Make" },
  { id: "use", label: "Use" },
  { id: "final_use", label: "Final use" },
];
const percent = new Intl.NumberFormat("en-GB", { style: "percent", maximumFractionDigits: 2 });

export default async function setup(frame, ctx) {
  const update = () => refresh();
  const area = addSelect(frame.controls, { label: "Geographic area", items: await ctx.lists.areas, onChange: update });
  const contributor = addSelect(frame.controls, { label: "Contributor", items: await ctx.lists.contributors, onChange: update });
  const period = addSelect(frame.controls, { label: "Period", items: await ctx.lists.periods, onChange: update });
  const mode = addSelect(frame.controls, { label: "Mode", items: MODES, onChange: update });
  const view = createChart(frame.canvas);

  async function refresh() {
    const path = `product_composition/${ctx.main().id}/${area.value}/${contributor.value}/${period.value}/${mode.value}`;
    const rows = await frame.run(path, () => getJSON(path));
    if (!rows) return;
    if (!rows.length) {
      return frame.showMessage(
        `No data to display for ${ctx.main().label} in ${area.label} by ${contributor.label}.`);
    }
    const total = rows.reduce((sum, r) => sum + Number(r.cmp_value), 0) || 1;
    view.render({
      tooltip: { formatter: (p) => `${escapeHtml(p.name)}: <strong>${percent.format(p.value / total)}</strong>` },
      legend: { bottom: 0, type: "scroll" },
      series: [{
        type: "pie",
        radius: ["40%", "75%"],
        center: ["50%", "70%"],
        startAngle: 180,
        endAngle: 360,
        label: { formatter: (p) => `${p.name}\n${percent.format(p.value / total)}` },
        data: rows.map((r) => ({ name: r.element_label, value: Number(r.cmp_value) })),
      }],
    });
  }
  return update;
}
