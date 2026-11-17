from collections import defaultdict

import pytest
from fastapi.testclient import TestClient

from panorama_api.db import ALLOWED_VIEWS
from panorama_api.main import app


class FakeDatabase:
    """In-memory stand-in for PostgresDatabase. Compares values as strings,
    because the API passes IDs as strings and PostgreSQL casts them."""

    def __init__(self):
        self.rows = defaultdict(list)
        self.calls = []

    def add(self, view, *rows):
        assert view in ALLOWED_VIEWS
        self.rows[view].extend(rows)

    def _match(self, view, where):
        assert view in ALLOWED_VIEWS, view
        return [r for r in self.rows[view]
                if all(str(r.get(k)) == str(v) for k, v in (where or {}).items())]

    def select(self, view, where=None, order_by=None):
        self.calls.append(("select", view, dict(where or {})))
        rows = self._match(view, where)
        if order_by:
            rows = sorted(rows, key=lambda r: r[order_by])
        return [dict(r) for r in rows]

    def total(self, view, sum_field, group_field, where):
        self.calls.append(("total", view, dict(where)))
        sums = {}
        for r in self._match(view, where):
            sums[r[group_field]] = sums.get(r[group_field], 0) + (r[sum_field] or 0)
        return [{group_field: k, "nb": v} for k, v in sums.items()]


@pytest.fixture
def db():
    return FakeDatabase()


@pytest.fixture
def client(db):
    app.state.db = db
    with TestClient(app) as c:
        yield c
    del app.state.db
