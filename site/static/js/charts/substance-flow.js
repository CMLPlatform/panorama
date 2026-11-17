// Flow of an element through the life cycle in an area: Sankey diagram.
import { getJSON } from "../lib/api.js";
import { createChart } from "../lib/chart.js";
import { formatTonnes, escapeHtml } from "../lib/format.js";
import { addSelect } from "../lib/ui.js";

export default async function setup(frame, ctx) {
  const update = () => refresh();
  const byCommodity = ctx.mode === "commodity";
  const other = byCommodity
    ? addSelect(frame.controls, { label: "Geographic area", items: await ctx.lists.areas, onChange: update })
    : addSelect(frame.controls, { label: "Element", items: await ctx.lists.elements, onChange: update });
  const period = addSelect(frame.controls, { label: "Period", items: await ctx.lists.periods, onChange: update });
  const view = createChart(frame.canvas);

  async function refresh() {
    const element = byCommodity ? ctx.main().id : other.value;
    const area = byCommodity ? other.value : ctx.main().id;
    const path = `substance_flow/${element}/${area}/${period.value}`;
    const rows = await frame.run(path, () => getJSON(path));
    if (!rows) return;
    const links = rows.filter((r) => r.from && r.to && Number(r.value) > 0)
      .map((r) => ({ source: r.from, target: r.to, value: Number(r.value) }));
    if (!links.length) {
      const [e, a] = byCommodity ? [ctx.main().label, other.label] : [other.label, ctx.main().label];
      return frame.showMessage(`No data to display for ${e} in ${a}.`);
    }
    const names = [...new Set(links.flatMap((l) => [l.source, l.target]))];
    try {
      view.render({
        tooltip: {
          formatter: (p) => (p.dataType === "edge"
            ? `${escapeHtml(p.data.source)} → ${escapeHtml(p.data.target)}<br><strong>${formatTonnes(p.value)}</strong>`
            : `${escapeHtml(p.name)}<br><strong>${formatTonnes(p.value)}</strong>`),
        },
        series: [{
          type: "sankey",
          left: 8, right: 160, top: 16, bottom: 16,
          nodeGap: 14,
          emphasis: { focus: "adjacency" },
          lineStyle: { color: "gradient", curveness: 0.5, opacity: 0.4 },
          label: { fontSize: 11, width: 150, overflow: "truncate" },
          data: names.map((name) => ({ name })),
          links,
        }],
      });
    } catch (error) {
      // ECharts refuses flows that loop back on themselves.
      console.error(error);
      frame.showMessage("These flows cannot be drawn as a diagram. Download the data to see them.");
    }
  }
  return update;
}
