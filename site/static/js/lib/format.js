// Number formatting: at most 2 decimals, with k (thousand), M (million) and
// G (billion) suffixes, like the "#.## a" format of the old charts.
const UNITS = [
  [1e12, "T"],
  [1e9, "G"],
  [1e6, "M"],
  [1e3, "k"],
];
const plain = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 2 });

export function formatNumber(value) {
  const n = Number(value);
  if (value === null || value === undefined || !Number.isFinite(n)) return "–";
  for (const [size, suffix] of UNITS) {
    if (Math.abs(n) >= size) return plain.format(n / size) + suffix;
  }
  return plain.format(n);
}

export const formatTonnes = (value) => `${formatNumber(value)} t`;

export function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}
