// Calls to the PANORAMA data API. Responses are cached for the page's lifetime.
const BASE = "/panorama/";
const cache = new Map();

export function getJSON(path) {
  if (!cache.has(path)) {
    const request = fetch(BASE + path, { headers: { Accept: "application/json" } })
      .then((response) => {
        if (!response.ok) throw new Error(`The server answered ${response.status} for ${path}`);
        return response.json();
      })
      .catch((error) => {
        cache.delete(path); // Let the next call try again.
        throw error;
      });
    cache.set(path, request);
  }
  return cache.get(path);
}

export const downloadUrl = (path) => `${BASE}${path}/download`;

// Code lists, sorted by label. The "rest" entry (for example "Rest of the World")
// goes to the end, as on the old site.
const REST_IDS = { geographic_areas: 1, elements: 9 };

export async function codeList(name) {
  const items = (await getJSON(name)).filter((item) => item.id != null && item.label);
  const rest = REST_IDS[name];
  return [...items].sort((a, b) => {
    if (a.id === rest) return 1;
    if (b.id === rest) return -1;
    return a.label.localeCompare(b.label);
  });
}
