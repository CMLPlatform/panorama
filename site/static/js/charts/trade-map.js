// Import or export map. Countries show their total; a click on a country shows
// its flows as lines and as a list. Used on the commodity and product pages.
import { getJSON, downloadUrl } from "../lib/api.js";
import { createChart } from "../lib/chart.js";
import { loadGeo } from "../lib/geo.js";
import { renderMap } from "../lib/map.js";
import { formatTonnes, escapeHtml } from "../lib/format.js";
import { addSelect } from "../lib/ui.js";

const DEMAND = [
  { id: "none", label: "Global" },
  { id: "intermediate_demand", label: "Intermediate demand only" },
  { id: "final_demand", label: "Final demand only" },
];

export default async function setup(frame, ctx) {
  const direction = ctx.name; // "import" or "export"
  const byProduct = ctx.mode === "product";
  const prefix = byProduct ? "product_" : "element_";
  const update = () => refresh();
  const period = addSelect(frame.controls, { label: "Period", items: await ctx.lists.periods, onChange: update });
  const demand = byProduct
    ? addSelect(frame.controls, { label: "Demand", items: DEMAND, onChange: update })
    : null;
  const suffix = () => (demand ? `/${demand.value}` : "");
  const labels = await loadGeo();
  const view = createChart(frame.canvas);
  frame.canvas.classList.add("map");
  frame.extra.innerHTML = '<p class="muted">Select a country on the map to see its flows.</p>';

  let values = new Map();
  let selected = null;
  let flowToken = 0;

  async function refresh() {
    selected = null;
    const path = `${prefix}${direction}_total/${ctx.main().id}/${period.value}${suffix()}`;
    const rows = await frame.run(path, () => getJSON(path));
    if (!rows) return;
    values = new Map(rows.map((r) => [r.country, Number(r.nb)]));
    showFlows(null);
  }

  async function showFlows(code) {
    selected = code;
    const mine = ++flowToken;
    if (!code) {
      renderMap(view, { labels, values });
      frame.extra.innerHTML = '<p class="muted">Select a country on the map to see its flows.</p>';
      return;
    }
    const path = `${prefix}${direction}_flow/${ctx.main().id}/${period.value}/${code}${suffix()}`;
    frame.extra.innerHTML = '<p class="muted">Loading flows…</p>';
    let rows;
    try {
      rows = await getJSON(path);
    } catch (error) {
      console.error(error);
      frame.extra.innerHTML = '<p class="error">The flows could not be loaded.</p>';
      return;
    }
    if (mine !== flowToken) return;
    const flows = rows.map((r) => ({ from: r.source_region, to: r.target_region, value: Number(r.value) }))
      .filter((f) => f.value > 0)
      .sort((a, b) => b.value - a.value);
    renderMap(view, { labels, values, selected: code, flows });

    const name = (c) => labels[c]?.name ?? c;
    const [heading, word, partner] = direction === "import"
      ? [`Imports into ${name(code)}`, "from", "from"]
      : [`Exports from ${name(code)}`, "to", "to"];
    const items = flows.map((f) => `<li><strong>${formatTonnes(f.value)}</strong> ${word} `
      + `${escapeHtml(name(f[partner]))}</li>`);
    frame.extra.innerHTML = `
      <div class="flow-list">
        <h3>${escapeHtml(heading)} <a class="download" href="${downloadUrl(path)}">Download (JSON)</a></h3>
        <ol>${items.join("") || "<li>None</li>"}</ol>
        <button type="button" class="link-button">Clear selection</button>
      </div>`;
    frame.extra.querySelector("button").addEventListener("click", () => showFlows(null));
  }

  view.chart.on("click", (event) => {
    if (event.componentType !== "geo" && event.seriesType !== "map") return;
    const code = event.name;
    showFlows(code === selected ? null : code);
  });
  return update;
}
