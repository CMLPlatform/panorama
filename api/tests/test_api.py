"""Behaviour of the API, compared with the old Drupal DataAccessController."""
import pytest


def test_periods_are_renamed_to_id_and_label(client, db):
    db.add("diffusion.filtered_period", {"id_period": 7, "period_label": "2016"})
    assert client.get("/panorama/periods").json() == [{"id": 7, "label": "2016"}]


def test_products_are_sorted_by_label(client, db):
    db.add("diffusion.filtered_product",
           {"id": 2, "product_label": "Zinc ores"}, {"id": 1, "product_label": "Copper wire"})
    assert [p["label"] for p in client.get("/panorama/products").json()] == [
        "Copper wire", "Zinc ores"]


def test_final_demand_groups_contributors_by_isic(client, db):
    db.add("diffusion.product_use_by_country_by_final_demand",
           {"id_geographicarea": 1, "id_product": 5, "id_period": 3,
            "contributor_isic": "Households", "contributor_label": "Food", "use_value": 2.5},
           {"id_geographicarea": 1, "id_product": 5, "id_period": 3,
            "contributor_isic": None, "contributor_label": "Government", "use_value": None},
           {"id_geographicarea": 1, "id_product": 5, "id_period": 3,
            "contributor_isic": "Households", "contributor_label": "Cars", "use_value": 1},
           {"id_geographicarea": 2, "id_product": 5, "id_period": 3,
            "contributor_isic": "Other area", "contributor_label": "x", "use_value": 9})
    assert client.get("/panorama/final_demand/1/5/3").json() == [
        {"name": "Households", "children": [{"name": "Food", "value": 2.5},
                                            {"name": "Cars", "value": 1}]},
        {"name": "Government", "children": [{"name": "Government", "value": 0}]},
    ]


def test_economic_sector_pivots_contributors_into_keys(client, db):
    base = {"id_element": 9, "id_geographicarea": 1, "id_period": 3}
    db.add("diffusion.element_use_by_country_by_economic_sector",
           {**base, "contributor_isic": "C", "contributor_label": "Metals", "use_value": 4},
           {**base, "contributor_isic": "C", "contributor_label": "Cables", "use_value": 1},
           {**base, "contributor_isic": "F", "contributor_label": "Buildings", "use_value": 2})
    assert client.get("/panorama/economic_sector/9/1/3").json() == [
        {"isic": "C", "Metals": 4, "Cables": 1}, {"isic": "F", "Buildings": 2}]


def test_economic_sector_without_data_is_empty_list(client):
    # The old API returned [{"isic": ""}] here.
    assert client.get("/panorama/economic_sector/9/1/3").json() == []


@pytest.mark.parametrize("demand, view", [
    ("none", "diffusion.product_import_by_country"),
    ("intermediate_demand", "diffusion.product_import_by_country_intermediate_demand"),
    ("final_demand", "diffusion.product_import_by_country_final_demand"),
])
def test_product_import_total_uses_view_for_demand_filter(client, db, demand, view):
    db.add(view, {"id_product": 5, "id_period": 3, "geographicarea_code": "NLD",
                  "import_value": 12.0})
    assert client.get(f"/panorama/product_import_total/5/3/{demand}").json() == [
        {"id_product": 5, "id_period": 3, "country": "NLD", "nb": 12.0}]


def test_unknown_demand_filter_is_rejected(client, db):
    response = client.get("/panorama/product_import_total/5/3/pg_catalog")
    assert response.status_code == 422
    assert db.calls == []


@pytest.mark.parametrize("path", [
    "/panorama/periods/../secret",
    "/panorama/final_demand/1;DROP/5/3",
    "/panorama/element_import_flow/1/3/nld",
    "/panorama/element_import_flow/1/3/NLDX",
    "/panorama/product_composition/1/1/1/1/everything",
])
def test_invalid_parameters_are_rejected(client, db, path):
    assert client.get(path).status_code in (404, 422)
    assert db.calls == []


def test_element_import_total_sums_flows_by_target(client, db):
    db.add("diffusion.element_area_flow",
           {"id_element": 1, "id_period": 3, "source_region": "DEU", "target_region": "NLD",
            "global_use": 2},
           {"id_element": 1, "id_period": 3, "source_region": "FRA", "target_region": "NLD",
            "global_use": 3},
           {"id_element": 1, "id_period": 3, "source_region": "NLD", "target_region": "DEU",
            "global_use": 4})
    result = client.get("/panorama/element_import_total/1/3").json()
    assert sorted(result, key=lambda r: r["country"]) == [
        {"country": "DEU", "nb": 4}, {"country": "NLD", "nb": 5}]


def test_product_flow_copies_use_column_into_value(client, db):
    db.add("diffusion.product_area_flow_final_demand",
           {"id_product": 5, "id_period": 3, "source_region": "DEU", "target_region": "NLD",
            "final_use": 7})
    assert client.get("/panorama/product_import_flow/5/3/NLD/final_demand").json()[0][
        "value"] == 7
    assert client.get("/panorama/product_export_flow/5/3/DEU/final_demand").json()[0][
        "value"] == 7


def test_element_export_flow_filters_on_source(client, db):
    db.add("diffusion.element_area_flow",
           {"id_element": 1, "id_period": 3, "source_region": "NLD", "target_region": "ROW",
            "global_use": 4})
    assert client.get("/panorama/element_export_flow/1/3/NLD").json() == [
        {"id_element": 1, "id_period": 3, "source_region": "NLD", "target_region": "ROW",
         "value": 4}]
    assert client.get("/panorama/element_import_flow/1/3/NLD").json() == []


@pytest.mark.parametrize("mode, field", [
    ("make", "cmp_supply_value"), ("use", "cmp_intermuse_value"),
    ("final_use", "cmp_finaluse_value")])
def test_product_composition_selects_mode_and_drops_empty(client, db, mode, field):
    base = {"id_product": 5, "id_geographicarea": 1, "id_contributor": 2, "id_period": 3}
    db.add("diffusion.product_element_composition",
           {**base, "element_label": "Cu", field: 0.4},
           {**base, "element_label": "Ta", field: None})
    result = client.get(f"/panorama/product_composition/5/1/2/3/{mode}").json()
    assert [(r["element_label"], r["cmp_value"]) for r in result] == [("Cu", 0.4)]


def test_substance_flow_is_ordered_and_renamed(client, db):
    base = {"id_element": 1, "id_geographicarea": 1, "id_period": 3}
    db.add("diffusion.sankey_final_period_geographicarea_element",
           {**base, "ordre": 2, "from_d": "B", "to_f": "C", "value": 1},
           {**base, "ordre": 1, "from_d": "A", "to_f": "B", "value": 2})
    result = client.get("/panorama/substance_flow/1/1/3").json()
    assert [(r["from"], r["to"]) for r in result] == [("A", "B"), ("B", "C")]


def test_download_returns_attachment(client, db):
    db.add("diffusion.element_make_by_country",
           {"id_element": 1, "id_period": 3, "geographicarea_code": "SWE", "make_value": 5})
    response = client.get("/panorama/element_make/1/3/download")
    assert response.headers["content-disposition"] == 'attachment; filename="element_make.json"'
    assert '\n    ' in response.text  # pretty-printed
    assert response.json() == [{"id_element": 1, "id_period": 3, "country": "SWE",
                                "make_value": 5}]


def test_json_responses_can_be_cached(client, db):
    assert "max-age" in client.get("/panorama/periods").headers["cache-control"]
