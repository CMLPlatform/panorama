// Final demand of a product in an area, by sector and contributor: treemap.
// On the country page the user picks the product; on the product page, the area.
import { getJSON } from "../lib/api.js";
import { createChart } from "../lib/chart.js";
import { formatNumber, formatTonnes, escapeHtml } from "../lib/format.js";
import { addSelect } from "../lib/ui.js";

export default async function setup(frame, ctx) {
  const update = () => refresh();
  const byCountry = ctx.mode === "country";
  const other = byCountry
    ? addSelect(frame.controls, { label: "Product", items: await ctx.lists.products, onChange: update })
    : addSelect(frame.controls, { label: "Geographic area", items: await ctx.lists.areas, onChange: update });
  const period = addSelect(frame.controls, { label: "Period", items: await ctx.lists.periods, onChange: update });
  const view = createChart(frame.canvas);

  async function refresh() {
    const area = byCountry ? ctx.main().id : other.value;
    const product = byCountry ? other.value : ctx.main().id;
    const path = `final_demand/${area}/${product}/${period.value}`;
    const tree = await frame.run(path, () => getJSON(path));
    if (!tree) return;
    if (!tree.length) {
      const [p, a] = byCountry ? [other.label, ctx.main().label] : [ctx.main().label, other.label];
      return frame.showMessage(`No data to display for ${p} in ${a} for period ${period.label}.`);
    }
    view.render({
      tooltip: {
        formatter: (p) => `${escapeHtml(p.treePathInfo.slice(1).map((n) => n.name).join(" › "))}<br>`
          + `<strong>${formatTonnes(p.value)}</strong>`,
      },
      series: [{
        type: "treemap",
        roam: false,
        nodeClick: false,
        breadcrumb: { show: false },
        width: "100%",
        height: "100%",
        top: 0,
        data: tree,
        label: {
          formatter: (p) => (p.value ? `{b|${p.name}}\n${formatNumber(p.value)}` : ""),
          rich: { b: { fontWeight: "bold" } },
          overflow: "break",
        },
        levels: [
          { itemStyle: { borderWidth: 0, gapWidth: 4 } },
          // Sector level: show the sector name in a band above its contributors.
          { itemStyle: { borderColor: "#fff", borderWidth: 3, gapWidth: 2 },
            upperLabel: { show: true, height: 22, color: "#fff", fontWeight: "bold" } },
          { colorSaturation: [0.35, 0.55], itemStyle: { borderColorSaturation: 0.6, gapWidth: 1 } },
        ],
      }],
    });
  }
  return update;
}
