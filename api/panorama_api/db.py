"""Read-only access to the PANORAMA business database (PostgreSQL).

The API only reads from a fixed list of views. View and column names come
from code, never from the request, so they cannot be used for SQL injection.
"""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Mapping, Protocol, Sequence

from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

Row = dict[str, Any]

# Every view the API may read. A request for any other name is refused.
ALLOWED_VIEWS = frozenset(
    {
        "production.codelist_contributortype",
        "production.contributor",
        "diffusion.filtered_element",
        "diffusion.filtered_period",
        "diffusion.filtered_product",
        "diffusion.filtered_geographicarea",
        "diffusion.product_use_by_country_by_final_demand",
        "diffusion.element_use_by_country_by_economic_sector",
        "diffusion.element_use_by_country",
        "diffusion.element_make_by_country",
        "diffusion.element_area_flow",
        "diffusion.product_area_flow",
        "diffusion.product_area_flow_intermediate_demand",
        "diffusion.product_area_flow_final_demand",
        "diffusion.product_import_by_country",
        "diffusion.product_import_by_country_intermediate_demand",
        "diffusion.product_import_by_country_final_demand",
        "diffusion.product_export_by_country",
        "diffusion.product_export_by_country_intermediate_demand",
        "diffusion.product_export_by_country_final_demand",
        "diffusion.product_element_composition",
        "diffusion.sankey_final_period_geographicarea_element",
    }
)


class Database(Protocol):
    def select(
        self, view: str, where: Mapping[str, Any] | None = None, order_by: str | None = None
    ) -> list[Row]: ...

    def total(
        self, view: str, sum_field: str, group_field: str, where: Mapping[str, Any]
    ) -> list[Row]: ...


def _identifier(view: str) -> sql.Identifier:
    if view not in ALLOWED_VIEWS:
        raise ValueError(f"View not allowed: {view}")
    return sql.Identifier(*view.split("."))


def _where(where: Mapping[str, Any] | None) -> tuple[sql.Composable, list[Any]]:
    if not where:
        return sql.SQL(""), []
    parts = [sql.SQL("{} = %s").format(sql.Identifier(k)) for k in where]
    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(parts), list(where.values())


def _clean(row: Mapping[str, Any]) -> Row:
    """Convert PostgreSQL NUMERIC values to float so they serialise as JSON numbers."""
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in row.items()}


class PostgresDatabase:
    def __init__(self, conninfo: str, min_size: int = 1, max_size: int = 10) -> None:
        self.pool = ConnectionPool(
            conninfo,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row, "autocommit": True},
            open=False,
        )

    def open(self) -> None:
        self.pool.open()

    def close(self) -> None:
        self.pool.close()

    def _run(self, query: sql.Composable, params: Sequence[Any]) -> list[Row]:
        with self.pool.connection() as conn:
            # Defence in depth: the session cannot write, even if a bug tries to.
            conn.execute("SET default_transaction_read_only = on")
            return [_clean(r) for r in conn.execute(query, params).fetchall()]

    def select(self, view, where=None, order_by=None):
        clause, params = _where(where)
        query = sql.SQL("SELECT * FROM {}").format(_identifier(view)) + clause
        if order_by:
            query += sql.SQL(" ORDER BY {}").format(sql.Identifier(order_by))
        return self._run(query, params)

    def total(self, view, sum_field, group_field, where):
        clause, params = _where(where)
        query = (
            sql.SQL("SELECT {g}, SUM({s}) AS nb FROM {v}").format(
                g=sql.Identifier(group_field), s=sql.Identifier(sum_field), v=_identifier(view)
            )
            + clause
            + sql.SQL(" GROUP BY {}").format(sql.Identifier(group_field))
        )
        return self._run(query, params)


def conninfo_from_env() -> str:
    """Build the connection string from PANORAMA_DB_* environment variables."""
    if dsn := os.environ.get("PANORAMA_DB_DSN"):
        return dsn
    from psycopg.conninfo import make_conninfo

    return make_conninfo(
        host=os.environ.get("PANORAMA_DB_HOST", "localhost"),
        port=os.environ.get("PANORAMA_DB_PORT", "5432"),
        dbname=os.environ.get("PANORAMA_DB_NAME", "panorama"),
        user=os.environ.get("PANORAMA_DB_USER", "panorama_reader"),
        password=os.environ.get("PANORAMA_DB_PASSWORD", ""),
    )
