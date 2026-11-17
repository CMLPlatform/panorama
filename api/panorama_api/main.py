"""PANORAMA data API.

Read-only JSON endpoints for the charts. The paths are the same as in the old
Drupal site (/panorama/...), so existing links and downloads keep working.
Add /download to any data path to get the same data as a pretty-printed file.
"""
from __future__ import annotations

import functools
import json
from contextlib import asynccontextmanager
from enum import Enum
from typing import Annotated, Any, Callable

from fastapi import Depends, FastAPI, Path, Request
from fastapi.responses import JSONResponse, Response

from . import transforms as t
from .db import Database, PostgresDatabase, conninfo_from_env

# Path parameter types. IDs stay strings: PostgreSQL then casts them to the
# column type, whatever that type is.
Id = Annotated[str, Path(pattern=r"^\d{1,10}$")]
CountryCode = Annotated[str, Path(pattern=r"^[A-Z]{2,3}$")]


class DemandFilter(str, Enum):
    none = "none"
    intermediate_demand = "intermediate_demand"
    final_demand = "final_demand"


class CompositionMode(str, Enum):
    make = "make"
    use = "use"
    final_use = "final_use"


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not hasattr(app.state, "db"):
        db = PostgresDatabase(conninfo_from_env())
        db.open()
        app.state.db = db
    yield
    if isinstance(app.state.db, PostgresDatabase):
        app.state.db.close()


# The interactive docs page is off: it loads scripts from a CDN, which the site's
# Content-Security-Policy blocks. The machine-readable description stays available.
app = FastAPI(title="PANORAMA data API", lifespan=lifespan, docs_url=None,
              openapi_url="/panorama/openapi.json", redoc_url=None)


def get_db(request: Request) -> Database:
    return request.app.state.db


DB = Annotated[Database, Depends(get_db)]

# Cache data in browsers and proxies for one hour: the data changes only when
# a new dataset is loaded.
CACHE_HEADERS = {"Cache-Control": "public, max-age=3600"}


def data_route(path: str, filename: str) -> Callable:
    """Register a JSON endpoint at `path` and a file download at `path`/download."""

    def decorator(func: Callable[..., Any]) -> Callable:
        app.get(path, name=filename)(_as_json(func))
        app.get(path + "/download", name=filename + "_download")(_as_download(func, filename))
        return func

    return decorator


# functools.wraps keeps the signature, so FastAPI still sees the typed parameters.
def _as_json(func):
    @functools.wraps(func)
    def wrapper(**kwargs):
        return JSONResponse(func(**kwargs), headers=CACHE_HEADERS)

    return wrapper


def _as_download(func, filename):
    @functools.wraps(func)
    def wrapper(**kwargs):
        body = json.dumps(func(**kwargs), indent=4, ensure_ascii=False)
        return Response(
            body,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

    return wrapper


# --- Code lists (used to fill the selectors) --------------------------------


@data_route("/panorama/contributor_types", "contributor_types")
def contributor_types(db: DB):
    return t.rename(db.select("production.codelist_contributortype"),
                    {"contributortype_label": "label"})


@data_route("/panorama/elements", "elements")
def elements(db: DB):
    return t.rename(db.select("diffusion.filtered_element"), {"element_label": "label"})


@data_route("/panorama/periods", "periods")
def periods(db: DB):
    return t.rename(db.select("diffusion.filtered_period"),
                    {"period_label": "label", "id_period": "id"})


@data_route("/panorama/products", "products")
def products(db: DB):
    rows = t.rename(db.select("diffusion.filtered_product"), {"product_label": "label"})
    return sorted(rows, key=lambda r: r["label"] or "")


@data_route("/panorama/geographic_areas", "geographic_areas")
def geographic_areas(db: DB):
    return t.rename(
        db.select("diffusion.filtered_geographicarea"),
        {"id_geographicarea": "id", "geographicarea_label": "label",
         "geographicarea_code": "code"},
    )


@data_route("/panorama/contributors", "contributors")
def contributors(db: DB):
    return t.rename(db.select("production.contributor"),
                    {"id_contributor": "id", "contributor_label": "label"})


# --- Chart data ---------------------------------------------------------------


@data_route("/panorama/final_demand/{area}/{product}/{period}", "final_demand")
def final_demand(db: DB, area: Id, product: Id, period: Id):
    rows = db.select("diffusion.product_use_by_country_by_final_demand",
                     {"id_geographicarea": area, "id_product": product, "id_period": period})
    return t.final_demand_tree(rows)


@data_route("/panorama/economic_sector/{substance}/{area}/{period}", "economic_sector")
def economic_sector(db: DB, substance: Id, area: Id, period: Id):
    rows = db.select("diffusion.element_use_by_country_by_economic_sector",
                     {"id_element": substance, "id_geographicarea": area, "id_period": period})
    return t.economic_sector_table(rows)


def _product_total_view(direction: str, demand: DemandFilter) -> str:
    view = f"diffusion.product_{direction}_by_country"
    return view if demand is DemandFilter.none else f"{view}_{demand.value}"


def _product_flow_view(demand: DemandFilter) -> str:
    view = "diffusion.product_area_flow"
    return view if demand is DemandFilter.none else f"{view}_{demand.value}"


@data_route("/panorama/product_import_total/{substance}/{period}/{filter}", "product_import_total")
def product_import_total(db: DB, substance: Id, period: Id, filter: DemandFilter):
    rows = db.select(_product_total_view("import", filter),
                     {"id_product": substance, "id_period": period})
    return t.rename(rows, {"geographicarea_code": "country", "import_value": "nb"})


@data_route("/panorama/product_export_total/{substance}/{period}/{filter}", "product_export_total")
def product_export_total(db: DB, substance: Id, period: Id, filter: DemandFilter):
    rows = db.select(_product_total_view("export", filter),
                     {"id_product": substance, "id_period": period})
    return t.rename(rows, {"geographicarea_code": "country", "export_value": "nb"})


@data_route("/panorama/element_import_total/{element}/{period}", "element_import_total")
def element_import_total(db: DB, element: Id, period: Id):
    rows = db.total("diffusion.element_area_flow", "global_use", "target_region",
                    {"id_element": element, "id_period": period})
    return t.rename(rows, {"target_region": "country"})


@data_route("/panorama/element_export_total/{element}/{period}", "element_export_total")
def element_export_total(db: DB, element: Id, period: Id):
    rows = db.total("diffusion.element_area_flow", "global_use", "source_region",
                    {"id_element": element, "id_period": period})
    return t.rename(rows, {"source_region": "country"})


@data_route("/panorama/product_import_flow/{substance}/{period}/{country}/{filter}",
            "product_import_flow")
def product_import_flow(db: DB, substance: Id, period: Id, country: CountryCode,
                        filter: DemandFilter):
    rows = db.select(_product_flow_view(filter),
                     {"id_product": substance, "id_period": period, "target_region": country})
    return t.product_flows(rows)


@data_route("/panorama/product_export_flow/{substance}/{period}/{country}/{filter}",
            "product_export_flow")
def product_export_flow(db: DB, substance: Id, period: Id, country: CountryCode,
                        filter: DemandFilter):
    rows = db.select(_product_flow_view(filter),
                     {"id_product": substance, "id_period": period, "source_region": country})
    return t.product_flows(rows)


@data_route("/panorama/element_import_flow/{element}/{period}/{country}", "element_import_flow")
def element_import_flow(db: DB, element: Id, period: Id, country: CountryCode):
    rows = db.select("diffusion.element_area_flow",
                     {"id_element": element, "id_period": period, "target_region": country})
    return t.rename(rows, {"global_use": "value"})


@data_route("/panorama/element_export_flow/{element}/{period}/{country}", "element_export_flow")
def element_export_flow(db: DB, element: Id, period: Id, country: CountryCode):
    rows = db.select("diffusion.element_area_flow",
                     {"id_element": element, "id_period": period, "source_region": country})
    return t.rename(rows, {"global_use": "value"})


@data_route("/panorama/country_use/{area}/{period}", "use_by_country")
def country_use(db: DB, area: Id, period: Id):
    return db.select("diffusion.element_use_by_country",
                     {"id_geographicarea": area, "id_period": period})


@data_route("/panorama/product_composition/{product}/{area}/{contributor}/{period}/{mode}",
            "product_composition")
def product_composition(db: DB, product: Id, area: Id, contributor: Id, period: Id,
                        mode: CompositionMode):
    rows = db.select("diffusion.product_element_composition",
                     {"id_product": product, "id_geographicarea": area,
                      "id_contributor": contributor, "id_period": period})
    return t.product_composition(rows, mode.value)


@data_route("/panorama/substance_flow/{commodity}/{area}/{period}", "substance_flow")
def substance_flow(db: DB, commodity: Id, area: Id, period: Id):
    rows = db.select("diffusion.sankey_final_period_geographicarea_element",
                     {"id_element": commodity, "id_geographicarea": area, "id_period": period},
                     order_by="ordre")
    return t.rename(rows, {"from_d": "from", "to_f": "to"})


@data_route("/panorama/element_make/{commodity}/{period}", "element_make")
def element_make(db: DB, commodity: Id, period: Id):
    rows = db.select("diffusion.element_make_by_country",
                     {"id_element": commodity, "id_period": period})
    return t.rename(rows, {"geographicarea_code": "country"})


@app.get("/panorama/health", include_in_schema=False)
def health():
    return {"status": "ok"}
