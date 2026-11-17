// Small UI helpers shared by all charts.
import { downloadUrl } from "./api.js";

let counter = 0;

/** Add a labelled <select> to `container`. Returns an object to read the choice. */
export function addSelect(container, { label, items, onChange, value }) {
  const id = `control-${++counter}`;
  const wrapper = document.createElement("div");
  wrapper.className = "control";
  wrapper.innerHTML = `<label for="${id}"></label><select id="${id}"></select>`;
  wrapper.querySelector("label").textContent = label;
  const select = wrapper.querySelector("select");
  for (const item of items) {
    const option = new Option(item.label, item.id);
    select.add(option);
  }
  if (value !== undefined) select.value = String(value);
  select.addEventListener("change", onChange);
  container.append(wrapper);
  return {
    get value() { return select.value; },
    get label() { return select.selectedOptions[0]?.textContent ?? ""; },
  };
}

/** Add a labelled checkbox. */
export function addCheckbox(container, { label, onChange, checked = false }) {
  const id = `control-${++counter}`;
  const wrapper = document.createElement("div");
  wrapper.className = "control control-checkbox";
  wrapper.innerHTML = `<input type="checkbox" id="${id}"><label for="${id}"></label>`;
  wrapper.querySelector("label").textContent = label;
  const box = wrapper.querySelector("input");
  box.checked = checked;
  box.addEventListener("change", onChange);
  container.append(wrapper);
  return { get checked() { return box.checked; } };
}

/** Status, loading and download handling for one chart section. */
export function chartFrame(section) {
  const status = section.querySelector(".chart-status");
  const controls = section.querySelector(".chart-controls");
  const download = document.createElement("a");
  download.className = "download";
  download.textContent = "Download data (JSON)";
  download.hidden = true;
  controls.after(download);
  let token = 0;

  return {
    section,
    controls,
    canvas: section.querySelector(".chart-canvas"),
    extra: section.querySelector(".chart-extra"),
    setTitle(text) {
      section.querySelector(".chart-title .selected").textContent = text;
    },
    /** Run `load` and ignore its result when a newer request started meanwhile. */
    async run(path, load) {
      const mine = ++token;
      section.classList.add("is-loading");
      status.textContent = "Loading…";
      download.href = downloadUrl(path);
      try {
        const result = await load();
        if (mine !== token) return;
        download.hidden = false;
        status.textContent = "";
        section.classList.remove("is-empty");
        return result;
      } catch (error) {
        if (mine !== token) return;
        console.error(error);
        this.showMessage("The data could not be loaded. Please try again later.");
      } finally {
        if (mine === token) section.classList.remove("is-loading");
      }
    },
    showMessage(text) {
      section.classList.add("is-empty");
      download.hidden = true;
      status.textContent = text;
    },
  };
}
