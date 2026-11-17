"""Build the static PANORAMA website into dist/.

Usage:
    python build.py [--out dist]

Content lives in content/ (Markdown and YAML). Layout lives in templates/.
Static files (CSS, JavaScript, images, map data) live in static/.
Set PANORAMA_NOTICE to show a banner on every page, for example to say that
the site shows synthetic data.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"

SITE = {
    "name": "PANORAMA",
    "slogan": "Physical accounts of raw material stock and flow information service",
    "menu": [
        {"title": "Access data", "url": "/", "children": [
            {"title": "By country", "url": "/data-by-country"},
            {"title": "By commodity", "url": "/data-by-commodity"},
            {"title": "By product", "url": "/data-by-product"}]},
        {"title": "Deliverables", "url": "/deliverables"},
        {"title": "Documents", "url": "/documents"},
        {"title": "Education", "children": [
            {"title": "Material Flow Analysis", "url": "/material-flow-analysis"},
            {"title": "Summer School 2020", "url": "/summer-school-2020"}]},
        {"title": "About", "children": [
            {"title": "About PANORAMA", "url": "/about"},
            {"title": "Methods", "url": "/methods"},
            {"title": "Terms of use", "url": "/terms-of-use"}]},
    ],
    "footer": [
        {"title": "Data policy", "url": "/usage"},
        {"title": "Legal information", "url": "/mention"},
        {"title": "Terms of use", "url": "/terms-of-use"},
    ],
}

# The three data pages: which selector and which charts each one shows.
DATA_PAGES = {
    "data-by-country": {"title": "Data by country", "mode": "country",
                        "charts": ["country-use", "final-demand"]},
    "data-by-commodity": {"title": "Data by commodity", "mode": "commodity",
                          "charts": ["economic-sector", "substance-flow", "import", "export",
                                     "element-make"]},
    "data-by-product": {"title": "Data by product", "mode": "product",
                        "charts": ["final-demand", "product-composition", "import", "export"]},
}

_md = markdown.Markdown(extensions=["tables", "attr_list", "sane_lists"])


def render_md(text: str | None) -> Markup:
    _md.reset()
    return Markup(_md.convert(text or ""))


def read_page(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf8")
    if text.startswith("---\n"):
        _, front, body = text.split("---\n", 2)
        return yaml.safe_load(front) or {}, body
    return {}, text


def read_yaml(name: str) -> dict:
    return yaml.safe_load((CONTENT / name).read_text(encoding="utf8")) or {}


def block(name: str) -> Markup:
    path = CONTENT / "blocks" / f"{name}.md"
    return render_md(path.read_text(encoding="utf8")) if path.exists() else Markup("")


SEARCH_FIELDS = ("title", "creator", "contributor", "subject", "type", "year", "coverage",
                 "description")


def search_text(doc: dict) -> str:
    """Lower-case text that the document search in the browser matches against."""
    return " ".join(str(doc[f]) for f in SEARCH_FIELDS if doc.get(f)).lower()


def asset_versions(static: Path) -> dict[str, str]:
    """Short content hash per static file, used to bust browser caches."""
    return {str(p.relative_to(static)): hashlib.sha256(p.read_bytes()).hexdigest()[:10]
            for p in static.rglob("*") if p.is_file()}


def build(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ROOT / "static", out / "static")
    if (CONTENT / "files").exists():
        shutil.copytree(CONTENT / "files", out / "files")

    versions = asset_versions(ROOT / "static")
    # Default Undefined: optional content fields (for example `file`) may be missing.
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True,
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["markdown"] = render_md
    env.globals.update(
        site=SITE, block=block, search_text=search_text, notice=os.environ.get("PANORAMA_NOTICE", ""),
        asset=lambda p: f"/static/{p}?v={versions[p]}",
    )

    def write(url_path: str, template: str, **context) -> None:
        target = out / url_path.strip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        html = env.get_template(template).render(current=url_path, **context)
        target.write_text(html, encoding="utf8")

    deliverables = read_yaml("deliverables.yaml")
    extras = {
        "deliverables": {"file_groups": deliverables.get("groups", []),
                         "after": "deliverables-disclaimer"},
        "material-flow-analysis": {"file_groups": deliverables.get("resources", [])},
    }
    for path in sorted((CONTENT / "pages").glob("*.md")):
        meta, body = read_page(path)
        slug = path.stem
        if slug == "index":
            write("/", "home.html", page=meta, body=render_md(body))
        else:
            write(f"/{slug}", "page.html", page=meta, body=render_md(body),
                  **extras.get(slug, {}))

    for slug, conf in DATA_PAGES.items():
        write(f"/{slug}", "data.html", page=conf)

    write("/documents", "documents.html", page={"title": "Documents"},
          documents=read_yaml("documents.yaml").get("documents", []))
    (out / "404.html").write_text(env.get_template("404.html").render(current=""),
                                  encoding="utf8")
    print(f"Site built in {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    build(parser.parse_args().out)
