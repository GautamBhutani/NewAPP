from __future__ import annotations

import pytest

from url_shortener.validation import validate_alias, validate_url_field


def test_validate_url_field_accepts_http_and_https_with_host():
    ok_http, message_http = validate_url_field({"url": "http://example.com/path"})
    ok_https, message_https = validate_url_field({"url": "https://example.com/path"})

    assert ok_http is True
    assert ok_https is True
    assert message_http == ""
    assert message_https == ""


def test_validate_url_field_rejects_non_http_scheme_with_clear_message():
    is_valid, message = validate_url_field({"url": "ftp://example.com"})

    assert is_valid is False
    assert message == "only http and https URLs are allowed"


def test_validate_url_field_rejects_netloc_without_host():
    is_valid, message = validate_url_field({"url": "http://user@/path"})

    assert is_valid is False
    assert message == "url is invalid"


def test_validate_alias_enforces_length_and_character_rules():
    assert validate_alias("abc") is True
    assert validate_alias("a" * 30) is True
    assert validate_alias("ab") is False
    assert validate_alias("a" * 31) is False
    assert validate_alias("abc_123") is False
    assert validate_alias("abc.123") is False


@pytest.mark.parametrize(
    "url",
    [
        "http://exa mple.com",
        "http://example.com:abc",
        "http://example.com\n",
    ],
)
def test_validate_url_field_rejects_malformed_authority_or_port(url: str):
    is_valid, message = validate_url_field({"url": url})

    assert is_valid is False
    assert message == "url is invalid"
