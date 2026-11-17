// Production (make) of an element by country: map.
import { getJSON } from "../lib/api.js";
import { createChart } from "../lib/chart.js";
import { loadGeo } from "../lib/geo.js";
import { renderMap } from "../lib/map.js";
import { addSelect } from "../lib/ui.js";

export default async function setup(frame, ctx) {
  const update = () => refresh();
  const period = addSelect(frame.controls, { label: "Period", items: await ctx.lists.periods, onChange: update });
  const labels = await loadGeo();
  const view = createChart(frame.canvas);
  frame.canvas.classList.add("map");

  async function refresh() {
    const path = `element_make/${ctx.main().id}/${period.value}`;
    const rows = await frame.run(path, () => getJSON(path));
    if (!rows) return;
    if (!rows.length) return frame.showMessage(`No production data for ${ctx.main().label}.`);
    renderMap(view, { labels, values: new Map(rows.map((r) => [r.country, Number(r.make_value)])) });
  }
  return update;
}
