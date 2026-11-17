"""SQL building in PostgresDatabase, checked without a database server."""
from decimal import Decimal

import pytest
from psycopg import sql

from panorama_api import db as dbmod


def test_unknown_view_is_refused():
    with pytest.raises(ValueError):
        dbmod._identifier("public.users")


def test_where_clause_uses_placeholders():
    clause, params = dbmod._where({"id_period": "3", "target_region": "NLD"})
    assert isinstance(clause, sql.Composed)
    assert params == ["3", "NLD"]


def test_numeric_values_become_float():
    assert dbmod._clean({"v": Decimal("1.50"), "s": "x"}) == {"v": 1.5, "s": "x"}
