from __future__ import annotations


def test_ac_6_1_created_record_persists_across_restart_with_same_sqlite_db(
    make_client, db_path, shorten
):
    first_client = make_client(db_path)
    created = shorten(first_client, "http://example.com/persist-record")
    code = created.json()["code"]
    first_client.close()

    second_client = make_client(db_path)
    stats = second_client.get(f"/{code}/stats")

    assert stats.status_code == 200
    assert stats.json()["code"] == code
    assert stats.json()["url"] == "http://example.com/persist-record"


def test_ac_6_2_clickcount_persists_across_restart_with_same_sqlite_db(
    make_client, db_path, shorten
):
    first_client = make_client(db_path)
    created = shorten(first_client, "http://example.com/persist-clicks")
    code = created.json()["code"]

    first_client.get(f"/{code}", follow_redirects=False)
    first_client.get(f"/{code}", follow_redirects=False)
    first_client.close()

    second_client = make_client(db_path)
    stats = second_client.get(f"/{code}/stats")

    assert stats.status_code == 200
    assert stats.json()["clickCount"] == 2


def test_ac_6_3_alias_uniqueness_persists_across_restart_with_same_sqlite_db(
    make_client, db_path, shorten, assert_error_response
):
    alias = "persistent-alias"

    first_client = make_client(db_path)
    first = shorten(first_client, "http://example.com/persist-alias", alias=alias)
    assert first.status_code == 201
    first_client.close()

    second_client = make_client(db_path)
    duplicate = shorten(second_client, "http://example.com/new-url", alias=alias)

    assert_error_response(
        duplicate,
        409,
        "ALIAS_IN_USE",
        "alias is already in use",
        "alias",
    )


def test_ac_6_4_service_auto_initializes_schema_for_empty_sqlite_file(
    make_client, tmp_path, shorten
):
    db_path = tmp_path / "nested" / "url_shortener.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text("")

    client = make_client(db_path)
    created = shorten(client, "http://example.com/auto-setup")

    assert created.status_code == 201
    code = created.json()["code"]
    stats = client.get(f"/{code}/stats")
    assert stats.status_code == 200
