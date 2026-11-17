// Document search: show only documents whose metadata contain every typed word.
const input = document.getElementById("doc-query");
const count = document.getElementById("doc-count");
const docs = [...document.querySelectorAll("#doc-list .doc")];

function filter() {
  const words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
  let shown = 0;
  for (const doc of docs) {
    const match = words.every((word) => doc.dataset.search.includes(word));
    doc.hidden = !match;
    if (match) shown += 1;
  }
  count.textContent = `${shown} of ${docs.length} documents`;
}

input.addEventListener("input", filter);
filter();
