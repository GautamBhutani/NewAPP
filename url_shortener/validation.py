from __future__ import annotations

import re
from urllib.parse import urlsplit

ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9-]{3,30}$")
_WHITESPACE_PATTERN = re.compile(r"\s")


def validate_url_field(payload: dict[str, object]) -> tuple[bool, str]:
    if "url" not in payload:
        return False, "url is required"

    raw_url = payload["url"]
    if not isinstance(raw_url, str) or not raw_url.strip():
        return False, "url is invalid"

    parsed = urlsplit(raw_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        if parsed.scheme:
            return False, "only http and https URLs are allowed"
        return False, "url is invalid"

    if _WHITESPACE_PATTERN.search(raw_url):
        return False, "url is invalid"

    if not parsed.netloc or parsed.hostname is None:
        return False, "url is invalid"

    try:
        parsed.port
    except ValueError:
        return False, "url is invalid"

    return True, ""


def validate_alias(alias: object) -> bool:
    return isinstance(alias, str) and bool(ALIAS_PATTERN.fullmatch(alias))
