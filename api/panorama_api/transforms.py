"""Reshape database rows into the JSON the charts expect.

These functions are pure: rows in, JSON-ready data out. They reproduce the
behaviour of the old Drupal module `data_access` (DataAccessController.php).
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

Row = dict[str, Any]


def rename(rows: Iterable[Mapping[str, Any]], mapping: Mapping[str, str]) -> list[Row]:
    """Rename columns. A missing source column gives None, as in the old API."""
    out = []
    for row in rows:
        new = dict(row)
        for old, target in mapping.items():
            new[target] = new.pop(old, None)
        out.append(new)
    return out


def _sector_key(row: Mapping[str, Any]) -> Any:
    """Group by ISIC code. Fall back to the contributor label when there is no code."""
    isic = row.get("contributor_isic")
    return isic if isic is not None else row.get("contributor_label")


def _value(row: Mapping[str, Any], field: str) -> Any:
    value = row.get(field)
    return 0 if value is None else value


def final_demand_tree(rows: Iterable[Mapping[str, Any]]) -> list[Row]:
    """Two-level tree for the treemap: ISIC sector -> contributor.

    The old code grouped only consecutive rows, so its result depended on the
    database row order. This version groups all rows with the same sector and
    keeps the order in which each sector first appears.
    """
    groups: dict[Any, Row] = {}
    for row in rows:
        key = _sector_key(row)
        group = groups.setdefault(key, {"name": key, "children": []})
        group["children"].append(
            {"name": row.get("contributor_label"), "value": _value(row, "use_value")}
        )
    return [g for g in groups.values() if g["children"]]


def economic_sector_table(rows: Iterable[Mapping[str, Any]]) -> list[Row]:
    """One record per ISIC sector, with one key per contributor (stacked bars)."""
    groups: dict[Any, Row] = {}
    for row in rows:
        key = _sector_key(row)
        group = groups.setdefault(key, {"isic": key})
        group[row.get("contributor_label")] = _value(row, "use_value")
    return list(groups.values())


FLOW_VALUE_FIELDS = ("intermediate_use", "final_use", "global_use")


def product_flows(rows: Iterable[Mapping[str, Any]]) -> list[Row]:
    """Copy whichever use column the flow view has into a common `value` key."""
    out = []
    for row in rows:
        new = dict(row)
        for field in FLOW_VALUE_FIELDS:
            if new.get(field) is not None:
                new["value"] = new[field]
        out.append(new)
    return out


COMPOSITION_FIELDS = {
    "make": "cmp_supply_value",
    "use": "cmp_intermuse_value",
    "final_use": "cmp_finaluse_value",
}


def product_composition(rows: Iterable[Mapping[str, Any]], mode: str) -> list[Row]:
    renamed = rename(rows, {COMPOSITION_FIELDS[mode]: "cmp_value"})
    return [r for r in renamed if r["cmp_value"] is not None]
