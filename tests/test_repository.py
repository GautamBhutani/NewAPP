from __future__ import annotations

from url_shortener.repository import UrlRepository


def test_repository_insert_get_and_increment(tmp_path):
    db_path = tmp_path / "repo.sqlite3"
    repository = UrlRepository(db_path)

    assert repository.insert("abc12345", "http://example.com", "2026-10-18T10:11:12.123456Z") is True
    assert repository.insert("abc12345", "http://example.com", "2026-10-18T10:11:12.123456Z") is False

    record = repository.get("abc12345")
    assert record is not None
    assert record.click_count == 0

    redirected_url = repository.increment_click_count_and_get_url("abc12345")
    assert redirected_url == "http://example.com"

    updated = repository.get("abc12345")
    assert updated is not None
    assert updated.click_count == 1


def test_repository_data_available_from_new_instance_using_same_path(tmp_path):
    db_path = tmp_path / "shared.sqlite3"
    first = UrlRepository(db_path)
    assert first.insert("persist01", "http://example.com", "2026-10-18T10:11:12.123456Z") is True

    second = UrlRepository(db_path)
    record = second.get("persist01")
    assert record is not None
    assert record.url == "http://example.com"
