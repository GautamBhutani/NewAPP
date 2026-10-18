from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UrlRecord:
    code: str
    url: str
    created_at: str
    click_count: int


def to_stats_payload(record: UrlRecord) -> dict[str, object]:
    return {
        "code": record.code,
        "url": record.url,
        "createdAt": record.created_at,
        "clickCount": record.click_count,
    }


def to_create_payload(record: UrlRecord, short_url: str) -> dict[str, object]:
    payload = to_stats_payload(record)
    payload["shortUrl"] = short_url
    return payload
