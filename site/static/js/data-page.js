// Controller for the three data pages (by country, by commodity, by product).
// It fills the main selector, sets up each chart on the page, and updates all
// charts when the selection changes.
import { codeList } from "./lib/api.js";
import { chartFrame } from "./lib/ui.js";

const MAIN_LIST = { country: "geographic_areas", commodity: "elements", product: "products" };

const CHART_MODULES = {
  "country-use": "./charts/country-use.js",
  "final-demand": "./charts/final-demand.js",
  "economic-sector": "./charts/economic-sector.js",
  "substance-flow": "./charts/substance-flow.js",
  import: "./charts/trade-map.js",
  export: "./charts/trade-map.js",
  "element-make": "./charts/element-make.js",
  "product-composition": "./charts/product-composition.js",
};

const root = document.getElementById("charts");
const mode = root.dataset.mode;
const input = document.getElementById("main-select");

// Shared code lists. Each is fetched once, even when several charts use it.
const lists = {
  periods: codeList("periods"),
  areas: codeList("geographic_areas"),
  products: codeList("products"),
  elements: codeList("elements"),
  contributors: codeList("contributors"),
};

let selected = null; // { id, label }

async function setupMainSelector() {
  const items = await codeList(MAIN_LIST[mode]);
  if (mode === "product") {
    const options = document.getElementById("main-options");
    for (const item of items) options.append(new Option(item.label));
    input.placeholder = "Type to search, or pick from the list";
    input.value = items[0]?.label ?? "";
    const pick = () => {
      const match = items.find((item) => item.label === input.value);
      if (match && match.id !== selected?.id) select(match);
    };
    input.addEventListener("change", pick);
    input.addEventListener("input", pick);
    input.addEventListener("focus", () => input.select());
  } else {
    input.replaceChildren(...items.map((item) => new Option(item.label, item.id)));
    input.disabled = false;
    input.addEventListener("change", () => {
      select(items.find((item) => String(item.id) === input.value));
    });
  }
  return items[0];
}

const charts = [];

function select(item) {
  if (!item) return;
  selected = item;
  for (const chart of charts) {
    chart.frame.setTitle(item.label);
    chart.update();
  }
}

async function main() {
  const first = await setupMainSelector();
  const context = { mode, lists, main: () => selected };
  await Promise.all([...root.querySelectorAll("[data-chart]")].map(async (section) => {
    const name = section.dataset.chart;
    const module = await import(CHART_MODULES[name]);
    const frame = chartFrame(section);
    const update = await module.default(frame, { ...context, name });
    charts.push({ frame, update });
  }));
  select(first);
}

main().catch((error) => {
  console.error(error);
  root.insertAdjacentHTML("afterbegin",
    '<p class="error" role="alert">The data service is not available. Please try again later.</p>');
});
