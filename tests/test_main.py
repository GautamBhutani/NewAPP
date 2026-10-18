from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from url_shortener import main


def test_create_retries_generated_code_collisions_until_insert_succeeds(monkeypatch, tmp_path):
    db_path = tmp_path / "retry-collisions.sqlite3"
    app = main.create_app(db_path=db_path)
    client = TestClient(app)

    duplicate_code = "ABCD1234"
    unique_code = "WXYZ6789"

    first = client.post(
        "/shorten",
        json={
            "url": "http://example.com/seed",
            "alias": duplicate_code,
        },
    )
    assert first.status_code == 201

    state = {"calls": 0}

    def fake_generate_code() -> str:
        state["calls"] += 1
        if state["calls"] <= 120:
            return duplicate_code
        return unique_code

    monkeypatch.setattr(main, "_generate_code", fake_generate_code)

    created = client.post("/shorten", json={"url": "http://example.com/retry"})

    assert created.status_code == 201
    assert created.json()["code"] == unique_code
    assert state["calls"] == 121


@pytest.mark.parametrize(
    "url",
    [
        "http://exa mple.com",
        "http://example.com:abc",
        "http://example.com\n",
    ],
)
def test_create_rejects_malformed_authority_and_does_not_create_alias(url, tmp_path):
    db_path = tmp_path / "invalid-authority.sqlite3"
    app = main.create_app(db_path=db_path)
    client = TestClient(app)

    alias = "invalid-authority-alias"
    created = client.post("/shorten", json={"url": url, "alias": alias})

    assert created.status_code == 422
    assert created.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "url is invalid",
            "field": "url",
        }
    }

    stats = client.get(f"/{alias}/stats")
    assert stats.status_code == 404
