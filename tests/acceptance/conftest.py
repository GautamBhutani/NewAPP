from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

_UNSET = object()


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "url_shortener.sqlite3"


@pytest.fixture
def make_client():
    clients = []

    def _make(db_path, public_base_url: str | None = None):
        from fastapi.testclient import TestClient
        from url_shortener.main import create_app

        app = create_app(db_path=db_path, public_base_url=public_base_url)
        client = TestClient(app)
        clients.append(client)
        return client

    yield _make

    for client in clients:
        client.close()


@pytest.fixture
def assert_error_response():
    def _assert(response, status_code: int, code: str, message: str, field: str | None):
        assert response.status_code == status_code
        assert response.headers["content-type"].startswith("application/json")
        assert response.json() == {
            "error": {
                "code": code,
                "message": message,
                "field": field,
            }
        }

    return _assert


@pytest.fixture
def assert_iso8601_z_timestamp():
    def _assert(value: Any):
        assert isinstance(value, str)
        assert value
        assert value.endswith("Z")
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None
        assert parsed.utcoffset() == dt.timedelta(0)

    return _assert


@pytest.fixture
def shorten():
    def _shorten(client, url: Any, alias: Any = _UNSET):
        payload = {"url": url}
        if alias is not _UNSET:
            payload["alias"] = alias
        return client.post("/shorten", json=payload)

    return _shorten
