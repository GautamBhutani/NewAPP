from __future__ import annotations


def test_ac_4_1_known_code_redirect_returns_302(make_client, db_path, shorten):
    client = make_client(db_path)
    created = shorten(client, "http://example.com/redirect-302")
    code = created.json()["code"]

    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 302


def test_ac_4_2_known_code_redirect_sets_location_to_original_url_exactly(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    original_url = "https://Example.com:443/a/b?q=One%2FTwo#section"
    created = shorten(client, original_url)
    code = created.json()["code"]

    response = client.get(f"/{code}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == original_url


def test_ac_4_3_one_redirect_increments_clickcount_to_one(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    created = shorten(client, "http://example.com/click-once")
    code = created.json()["code"]

    redirect = client.get(f"/{code}", follow_redirects=False)
    stats = client.get(f"/{code}/stats")

    assert redirect.status_code == 302
    assert stats.status_code == 200
    assert stats.json()["clickCount"] == 1


def test_ac_4_4_three_redirects_increment_clickcount_by_three(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    created = shorten(client, "http://example.com/click-thrice")
    code = created.json()["code"]

    before = client.get(f"/{code}/stats")
    for _ in range(3):
        redirect = client.get(f"/{code}", follow_redirects=False)
        assert redirect.status_code == 302
    after = client.get(f"/{code}/stats")

    assert before.status_code == 200
    assert after.status_code == 200
    assert after.json()["clickCount"] - before.json()["clickCount"] == 3


def test_ac_4_5_unknown_code_redirect_returns_404_and_creates_no_record(
    make_client, db_path, assert_error_response
):
    client = make_client(db_path)
    unknown_code = "missing-code"

    redirect = client.get(f"/{unknown_code}", follow_redirects=False)

    assert_error_response(redirect, 404, "NOT_FOUND", "code not found", "code")
    stats = client.get(f"/{unknown_code}/stats")
    assert_error_response(stats, 404, "NOT_FOUND", "code not found", "code")


def test_ac_5_1_stats_for_existing_code_returns_200_with_expected_fields(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    created = shorten(client, "http://example.com/stats-fields")
    code = created.json()["code"]

    stats = client.get(f"/{code}/stats")

    assert stats.status_code == 200
    assert stats.headers["content-type"].startswith("application/json")
    assert set(stats.json()) == {"code", "url", "createdAt", "clickCount"}


def test_ac_5_2_stats_url_equals_exact_original_submitted_url(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    original_url = "https://Example.COM:4443/Exact/Case?keep=Yes%2FNo#Fragment"
    created = shorten(client, original_url)
    code = created.json()["code"]

    stats = client.get(f"/{code}/stats")

    assert stats.status_code == 200
    assert stats.json()["url"] == original_url


def test_ac_5_3_stats_createdat_is_creation_timestamp_and_not_changed_by_redirects(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    created = shorten(client, "http://example.com/stable-created-at")
    code = created.json()["code"]
    created_at = created.json()["createdAt"]

    first_stats = client.get(f"/{code}/stats")
    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)
    second_stats = client.get(f"/{code}/stats")

    assert first_stats.status_code == 200
    assert second_stats.status_code == 200
    assert first_stats.json()["createdAt"] == created_at
    assert second_stats.json()["createdAt"] == created_at


def test_ac_5_4_stats_clickcount_reflects_only_successful_redirect_requests(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    created = shorten(client, "http://example.com/click-source")
    code = created.json()["code"]

    unknown_redirect = client.get("/definitely-missing-code", follow_redirects=False)
    first_stats = client.get(f"/{code}/stats")
    client.get(f"/{code}", follow_redirects=False)
    client.get(f"/{code}", follow_redirects=False)
    second_stats = client.get(f"/{code}/stats")

    assert unknown_redirect.status_code == 404
    assert first_stats.status_code == 200
    assert second_stats.status_code == 200
    assert first_stats.json()["clickCount"] == 0
    assert second_stats.json()["clickCount"] == 2


def test_ac_5_5_repeated_stats_requests_do_not_increment_clickcount(
    make_client, db_path, shorten
):
    client = make_client(db_path)
    created = shorten(client, "http://example.com/stats-read-only")
    code = created.json()["code"]

    client.get(f"/{code}", follow_redirects=False)
    first_stats = client.get(f"/{code}/stats")
    second_stats = client.get(f"/{code}/stats")
    third_stats = client.get(f"/{code}/stats")

    assert first_stats.status_code == 200
    assert second_stats.status_code == 200
    assert third_stats.status_code == 200
    assert first_stats.json()["clickCount"] == 1
    assert second_stats.json()["clickCount"] == 1
    assert third_stats.json()["clickCount"] == 1


def test_ac_5_6_unknown_code_stats_returns_404_with_not_found_error(
    make_client, db_path, assert_error_response
):
    client = make_client(db_path)

    response = client.get("/unknown-code/stats")

    assert_error_response(response, 404, "NOT_FOUND", "code not found", "code")
