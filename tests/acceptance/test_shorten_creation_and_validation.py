from __future__ import annotations

import re

import pytest


def test_ac_1_1_create_http_url_returns_201_with_expected_body_fields(
    make_client, db_path, shorten
):
    client = make_client(db_path)

    response = shorten(client, "http://example.com")

    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert set(body) == {"code", "shortUrl", "url", "createdAt", "clickCount"}


def test_ac_1_2_create_https_url_stores_original_exactly_as_submitted(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    original_url = "https://Example.COM:8443/PaTh?q=A%2FZ&x=1#Frag"

    response = shorten(client, original_url)

    assert response.status_code == 201
    assert response.json()["url"] == original_url


def test_ac_1_3_create_success_response_clickcount_starts_at_zero(
    make_client, db_path, shorten
):
    client = make_client(db_path)

    response = shorten(client, "http://example.com/start-zero")

    assert response.status_code == 201
    assert response.json()["clickCount"] == 0


def test_ac_1_4_create_success_response_createdat_is_iso8601_utc_timestamp(
    make_client, db_path, shorten, assert_iso8601_z_timestamp
):
    client = make_client(db_path)

    response = shorten(client, "http://example.com/created-at")

    assert response.status_code == 201
    assert_iso8601_z_timestamp(response.json()["createdAt"])


def test_ac_1_5_generated_code_is_non_empty_eight_chars_and_unique(
    make_client, db_path, shorten
):
    client = make_client(db_path)

    first = shorten(client, "http://example.com/first")
    second = shorten(client, "http://example.com/second")

    assert first.status_code == 201
    assert second.status_code == 201

    first_code = first.json()["code"]
    second_code = second.json()["code"]

    assert first_code
    assert second_code
    assert re.fullmatch(r"[A-Za-z0-9]{8}", first_code)
    assert re.fullmatch(r"[A-Za-z0-9]{8}", second_code)
    assert first_code != second_code


def test_ac_1_6_two_creates_same_url_without_alias_make_distinct_non_overwriting_records(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    original_url = "http://example.com/same-target"

    first = shorten(client, original_url)
    second = shorten(client, original_url)

    assert first.status_code == 201
    assert second.status_code == 201

    first_code = first.json()["code"]
    second_code = second.json()["code"]
    assert first_code != second_code

    first_stats = client.get(f"/{first_code}/stats")
    second_stats = client.get(f"/{second_code}/stats")

    assert first_stats.status_code == 200
    assert second_stats.status_code == 200
    assert first_stats.json()["url"] == original_url
    assert second_stats.json()["url"] == original_url


def test_ac_2_1_missing_url_returns_422_with_required_error(
    make_client, db_path, assert_error_response
):
    client = make_client(db_path)

    response = client.post("/shorten", json={})

    assert_error_response(
        response,
        422,
        "VALIDATION_ERROR",
        "url is required",
        "url",
    )


def test_ac_2_2_empty_url_returns_422_with_invalid_error(
    make_client, db_path, assert_error_response
):
    client = make_client(db_path)

    response = client.post("/shorten", json={"url": "   "})

    assert_error_response(
        response,
        422,
        "VALIDATION_ERROR",
        "url is invalid",
        "url",
    )


def test_ac_2_3_non_http_scheme_returns_422_with_scheme_error(
    make_client, db_path, assert_error_response
):
    client = make_client(db_path)

    response = client.post("/shorten", json={"url": "ftp://example.com"})

    assert_error_response(
        response,
        422,
        "VALIDATION_ERROR",
        "only http and https URLs are allowed",
        "url",
    )


def test_ac_2_4_malformed_url_returns_422_and_creates_no_short_code(
    make_client, db_path, assert_error_response
):
    client = make_client(db_path)
    alias = "malformed-alias"

    response = client.post("/shorten", json={"url": "not-a-url", "alias": alias})

    assert_error_response(
        response,
        422,
        "VALIDATION_ERROR",
        "url is invalid",
        "url",
    )
    stats_response = client.get(f"/{alias}/stats")
    assert stats_response.status_code == 404


def test_ac_2_5_failed_invalid_create_never_produces_lookupable_code(
    make_client, db_path, assert_error_response
):
    client = make_client(db_path)
    alias = "failed-create"

    failed = client.post("/shorten", json={"url": "not-a-url", "alias": alias})

    assert_error_response(
        failed,
        422,
        "VALIDATION_ERROR",
        "url is invalid",
        "url",
    )

    redirect_response = client.get(f"/{alias}", follow_redirects=False)
    stats_response = client.get(f"/{alias}/stats")

    assert_error_response(
        redirect_response,
        404,
        "NOT_FOUND",
        "code not found",
        "code",
    )
    assert_error_response(
        stats_response,
        404,
        "NOT_FOUND",
        "code not found",
        "code",
    )


def test_ac_3_1_valid_custom_alias_is_accepted_and_returned_as_code(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    alias = "my-custom-alias-123"

    response = shorten(client, "https://example.com/alias-ok", alias=alias)

    assert response.status_code == 201
    assert response.json()["code"] == alias


def test_ac_3_2_duplicate_custom_alias_returns_409_in_use_error(
    make_client, db_path, shorten, assert_error_response
):
    client = make_client(db_path)
    alias = "used-alias"

    first = shorten(client, "https://example.com/first", alias=alias)
    duplicate = shorten(client, "https://example.com/second", alias=alias)

    assert first.status_code == 201
    assert_error_response(
        duplicate,
        409,
        "ALIAS_IN_USE",
        "alias is already in use",
        "alias",
    )


def test_ac_3_3_alias_shorter_than_three_is_rejected_without_record(
    make_client, db_path, shorten, assert_error_response
):
    client = make_client(db_path)
    alias = "ab"

    response = shorten(client, "http://example.com/too-short-alias", alias=alias)

    assert_error_response(
        response,
        422,
        "VALIDATION_ERROR",
        "alias must be 3-30 characters and contain only letters, digits, or hyphens",
        "alias",
    )
    stats_response = client.get(f"/{alias}/stats")
    assert stats_response.status_code == 404


def test_ac_3_4_alias_longer_than_thirty_is_rejected_without_record(
    make_client, db_path, shorten, assert_error_response
):
    client = make_client(db_path)
    alias = "a" * 31

    response = shorten(client, "http://example.com/too-long-alias", alias=alias)

    assert_error_response(
        response,
        422,
        "VALIDATION_ERROR",
        "alias must be 3-30 characters and contain only letters, digits, or hyphens",
        "alias",
    )
    stats_response = client.get(f"/{alias}/stats")
    assert stats_response.status_code == 404


@pytest.mark.parametrize("alias", ["abc_123", "abc.123"])
def test_ac_3_5_alias_with_disallowed_characters_is_rejected_without_record(
    make_client, db_path, shorten, assert_error_response, alias
):
    client = make_client(db_path)

    response = shorten(client, "http://example.com/invalid-alias-char", alias=alias)

    assert_error_response(
        response,
        422,
        "VALIDATION_ERROR",
        "alias must be 3-30 characters and contain only letters, digits, or hyphens",
        "alias",
    )
    stats_response = client.get(f"/{alias}/stats")
    assert stats_response.status_code == 404


def test_ac_3_6_alias_with_minimum_length_three_is_accepted(
    make_client, db_path, shorten
):
    client = make_client(db_path)

    response = shorten(client, "http://example.com/min-alias", alias="abc")

    assert response.status_code == 201


def test_ac_3_7_alias_with_maximum_length_thirty_is_accepted(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    alias = "a" * 30

    response = shorten(client, "http://example.com/max-alias", alias=alias)

    assert response.status_code == 201
