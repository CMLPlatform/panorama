"""One-off migration: export the old Drupal content to Markdown and YAML.

Usage (from 05_WEBSITE):
    python tools/export_drupal.py ../02_DRUPAL/docker/database/drupal/backup.sql \
        ../02_DRUPAL/docker/apache-php/drupal.data.tar site/content

It writes:
    pages/<slug>.md     one file per Drupal page, with YAML front matter
    blocks/<name>.md    reusable text blocks (disclaimers, chart help texts)
    deliverables.yaml   deliverables grouped by work package
    documents.yaml      the document library
    files/...           the PDFs and images that the content uses
Run it once. After that, edit the files in site/content directly.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import tarfile
from pathlib import Path
from urllib.parse import unquote

import yaml
from markdownify import markdownify

HERE = Path(__file__).parent
FILES_PREFIX = "/sites/default/files/"

PAGES = {  # nid -> slug. Nodes 2-4 are the data pages; they become templates.
    1: "index", 6: "about", 7: "methods", 8: "terms-of-use", 9: "material-flow-analysis",
    10: "summer-school-2020", 11: "deliverables", 12: "mention", 13: "usage",
}
BLOCKS = {  # block_content id -> file name
    1: "site-introduction", 2: "data-disclaimer", 3: "documents-disclaimer",
    4: "deliverables-disclaimer", 5: "chart-country-use", 6: "chart-import-export",
    7: "chart-final-demand", 8: "chart-economic-sector", 9: "chart-product-composition",
}
# Deliverable groups, in the order of the old /deliverables page (term id, title).
DELIVERABLE_GROUPS = [
    (1, "0 - Go-To-Market Strategy"), (2, "1 - Management And Dissemination Activities"),
    (3, "2 - Professional Development"), (4, "3 - Data Harvesting"),
    (5, "4 - Data Processing"), (6, "5 - Balancing"), (7, "6 - IT Infrastructure"),
]
RESOURCE_GROUPS = [(8, "Resources"), (9, "Summer School Documents")]


def load(dump: Path, tables: list[str]) -> dict:
    out = subprocess.run([sys.executable, str(HERE / "mysqldump_reader.py"), str(dump), *tables],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def safe_name(name: str) -> str:
    """Web-safe file path: no spaces, '+' or '&' (they break Markdown links and URLs)."""
    return "/".join(re.sub(r"[^A-Za-z0-9._-]+", "_", part) for part in name.split("/"))


def _rewrite_file_link(match: re.Match) -> str:
    return "/files/" + safe_name(unquote(match.group(1)))


def to_markdown(body: str | None) -> str:
    if not body:
        return ""
    # Links to the old site domain become site-relative links.
    body = re.sub(r"https?://(?:www\.)?panorama(?:\.brgm\.fr|project\.eu)(?=/)", "", body)
    body = re.sub(re.escape(FILES_PREFIX) + r'([^"\']+)', _rewrite_file_link, body)
    body = re.sub(r"</?span[^>]*>", "", body)
    md = markdownify(body, heading_style="ATX", bullets="-", strip=["span"],
                     keep_inline_images_in=["h1", "h2", "h3", "h4", "a"])
    md = re.sub(r"^#+ *(!\[[^\]]*\]\([^)]*\)) *$", r"\1", md, flags=re.M)  # image-only headings
    md = html.unescape(md).replace(" ", " ")
    md = re.sub(r"[ \t]+\n", "\n", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def write_md(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    front = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    path.write_text(f"---\n{front}\n---\n\n{body}", encoding="utf8")


def main(dump: Path, files_tar: Path, out: Path) -> None:
    d = load(dump, ["node_field_data", "node__body", "block_content__body", "file_managed",
                    "node__field_associated_file", "node__field_filter_term", "node__field_file",
                    "node__field_creator", "node__field_contributor", "node__field_coverage",
                    "node__field_description", "node__field_format", "node__field_language",
                    "node__field_subject", "node__field_type_list", "node__field_year"])
    nodes = {r["nid"]: r for r in d["node_field_data"]}
    bodies = {r["entity_id"]: r["body_value"] for r in d["node__body"]}
    files = {r["fid"]: r["uri"].removeprefix("public://") for r in d["file_managed"]}
    by_safe_name = {safe_name(n): n for n in files.values()}

    def field(table, col):
        return {r["entity_id"]: r[col] for r in d[table]}

    used_files: set[str] = set()
    for nid, slug in PAGES.items():
        body = to_markdown(bodies.get(nid))
        used_files.update(re.findall(r"/files/([^)\s\"]+)", body))
        write_md(out / "pages" / f"{slug}.md", {"title": nodes[nid]["title"]}, body)

    for r in d["block_content__body"]:
        if r["entity_id"] in BLOCKS:
            path = out / "blocks" / f"{BLOCKS[r['entity_id']]}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(to_markdown(r["body_value"]), encoding="utf8")

    assoc = field("node__field_associated_file", "field_associated_file_target_id")
    term = field("node__field_filter_term", "field_filter_term_target_id")

    def file_items(tid):
        items = []
        for nid in sorted((n for n, t in term.items() if t == tid),
                          key=lambda n: nodes[n]["title"]):
            item = {"title": nodes[nid]["title"].strip(),
                    "description": to_markdown(bodies.get(nid)).strip()}
            if nid in assoc:
                item["file"] = "/files/" + safe_name(files[assoc[nid]])
                used_files.add(safe_name(files[assoc[nid]]))
            items.append(item)
        return items

    deliverables = {
        "groups": [{"title": t, "items": file_items(tid)} for tid, t in DELIVERABLE_GROUPS],
        "resources": [{"title": t, "items": file_items(tid)} for tid, t in RESOURCE_GROUPS],
    }

    doc_file = field("node__field_file", "field_file_target_id")
    meta_fields = {"creator": "node__field_creator", "contributor": "node__field_contributor",
                   "coverage": "node__field_coverage", "format": "node__field_format",
                   "language": "node__field_language", "subject": "node__field_subject",
                   "type": "node__field_type_list", "year": "node__field_year"}
    meta = {k: field(tab, f"field_{tab.removeprefix('node__field_')}_value")
            for k, tab in meta_fields.items()}
    descriptions = field("node__field_description", "field_description_value")
    documents = []
    for nid in sorted(n for n, r in nodes.items() if r["type"] == "document"):
        doc = {"title": nodes[nid]["title"].strip()}
        doc.update({k: v[nid] for k, v in meta.items() if nid in v})
        doc["description"] = to_markdown(descriptions.get(nid)).strip()
        if nid in doc_file:
            doc["file"] = "/files/" + safe_name(files[doc_file[nid]])
            used_files.add(safe_name(files[doc_file[nid]]))
        documents.append(doc)

    dump_yaml = lambda obj, name: (out / name).write_text(
        yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=100), encoding="utf8")
    dump_yaml(deliverables, "deliverables.yaml")
    dump_yaml({"documents": documents}, "documents.yaml")

    # Copy only the files that the content uses (the archive has many duplicates).
    with tarfile.open(files_tar) as tar:
        by_safe_name[safe_name("logo small@4x.png")] = "logo small@4x.png"
        for name in sorted(used_files | {safe_name("logo small@4x.png")}):
            member = tar.getmember(by_safe_name[name])
            target = out / "files" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(tar.extractfile(member).read())
    print(f"Wrote {len(PAGES)} pages, {len(BLOCKS)} blocks, {len(documents)} documents, "
          f"{len(used_files)} files to {out}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
