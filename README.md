# PANORAMA website

This folder is the new PANORAMA website. It replaces the Drupal 9 site previously built in the PANORAMA project.
It has the same pages, charts and data downloads, but no content management system.

## Parts

| Folder | What it is |
|---|---|
| `api/` | Read-only data API (Python, FastAPI). It reads the PostgreSQL business database and returns JSON for the charts. |
| `site/` | Static website. Content is Markdown and YAML in `site/content/`. `build.py` turns it into HTML. |
| `site/static/` | CSS, JavaScript, map data, and the chart library (ECharts 5.6.0, stored locally). |
| `web/` | nginx configuration. nginx serves the site and forwards `/panorama/...` to the API. |
| `db/` | Database start-up scripts and the **synthetic** placeholder data. |
| `tools/` | One-off scripts: content export from Drupal, map data build. |

The API keeps the old URL paths (for example `/panorama/periods` or
`/panorama/final_demand/{area}/{product}/{period}`). Add `/download` to a data path to get a JSON file.

## Run it

You need Docker with Docker Compose v2.

```shell
cp .env.example .env      # then set two random passwords in .env
docker compose up -d --build
```

Open http://localhost:8080.

The first start loads the database. To reload the database from scratch, delete its volume:

```shell
docker compose down -v
docker compose up -d --build
```

## Synthetic data

By default the database holds **synthetic data**. The values are random and are not real.
Every page shows a banner that says so. The generator is `db/synthetic/generate.py`.
It creates the same 22 tables and columns that the API reads.

To make the data again:

```shell
python3 db/synthetic/generate.py > db/synthetic/10-synthetic.sql
```

## Change to the real data

1. Put the real PostgreSQL dump in a folder outside this repository, for example `../04_BUSINESS_DATA/`.
   The start-up script loads `*.sql`, `*.sql.gz` and `*.dump` (pg_dump custom format) files, in name order.
2. In `.env`, set `PANORAMA_DB_INIT=../04_BUSINESS_DATA` and remove the `PANORAMA_NOTICE` line.
3. Run `docker compose down -v` and then `docker compose up -d --build`.

Note: if the dump was made with `pg_dump --create`, remove its `CREATE DATABASE` and `\connect` lines first.
The database `panorama` already exists in the container.

**Check after the first load.** The synthetic tables use column names taken from the old PHP and
JavaScript code. If a real view uses another name, the chart for that view stays empty.
The API logs show the database error. Compare with the list of views in `api/panorama_api/db.py`.

## Edit content

| To change | Edit |
|---|---|
| A text page (About, Methods, …) | `site/content/pages/<name>.md` |
| Help text above a chart, disclaimers | `site/content/blocks/<name>.md` |
| Deliverables and resources lists | `site/content/deliverables.yaml` |
| Document library | `site/content/documents.yaml` |
| PDFs and images | `site/content/files/` |
| Menu and footer links | `SITE` in `site/build.py` |
| Charts on each data page | `DATA_PAGES` in `site/build.py` |

Then run `docker compose up -d --build web`.

To preview the site without Docker: `pip install -r site/requirements.txt`, then `python site/build.py`.
The output goes to `site/dist/`. The charts need the API, so use Docker for those.

## Tests

```shell
cd api
docker run --rm -v "$PWD":/app -w /app python:3.12-slim \
  sh -c "pip install -q -r requirements-dev.txt && python -m pytest -q"
```

The tests use an in-memory database. They check each endpoint against the behaviour of the old
Drupal module, and they check that invalid input is refused before any query runs.

## Differences from the Drupal site

- **No login and no web editor.** Content changes go through the files above (and git).
- **Document search** looks in the metadata and summaries only. The old site also searched inside
  the PDF text (Apache Solr and Tika).
- **Charts use ECharts** (Apache 2.0 licence) in place of amCharts 4 (commercial licence).
- **Maps use Eurostat GISCO borders.** The attribution "© EuroGeographics" is required and is on the pages.
- **Two bugs are fixed.** Sector grouping no longer depends on the database row order.
  An empty result is now `[]`, not `[{"isic": ""}]`.
- **Security.** The API reads through a database role that cannot write. It accepts only fixed view
  names and validated parameters. The database has no public port.
