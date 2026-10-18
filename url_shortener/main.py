from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from url_shortener.models import UrlRecord, to_create_payload, to_stats_payload
from url_shortener.repository import UrlRepository
from url_shortener.validation import validate_alias, validate_url_field

_GENERATED_CODE_CHARACTERS = string.ascii_letters + string.digits


def _utc_now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _error_response(status_code: int, code: str, message: str, field: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "field": field,
            }
        },
    )


def _generate_code() -> str:
    return "".join(secrets.choice(_GENERATED_CODE_CHARACTERS) for _ in range(8))


def create_app(
    db_path: str | Path = "url_shortener.sqlite3",
    public_base_url: str | None = None,
) -> FastAPI:
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    repository = UrlRepository(db_file)
    app = FastAPI()
    normalized_public_base_url = public_base_url.rstrip("/") if public_base_url else None

    @app.post("/shorten")
    async def shorten_url(request: Request) -> JSONResponse:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        if not isinstance(payload, dict):
            payload = {}

        is_valid_url, url_message = validate_url_field(payload)
        if not is_valid_url:
            return _error_response(
                status_code=422,
                code="VALIDATION_ERROR",
                message=url_message,
                field="url",
            )

        alias_present = "alias" in payload and payload.get("alias") is not None
        alias = payload.get("alias") if alias_present else None
        if alias_present and not validate_alias(alias):
            return _error_response(
                status_code=422,
                code="VALIDATION_ERROR",
                message="alias must be 3-30 characters and contain only letters, digits, or hyphens",
                field="alias",
            )

        submitted_url = cast(str, payload["url"])
        created_at = _utc_now_iso_z()

        if alias is not None:
            inserted = repository.insert(code=alias, url=submitted_url, created_at=created_at)
            if not inserted:
                return _error_response(
                    status_code=409,
                    code="ALIAS_IN_USE",
                    message="alias is already in use",
                    field="alias",
                )
            code = alias
        else:
            while True:
                candidate = _generate_code()
                inserted = repository.insert(code=candidate, url=submitted_url, created_at=created_at)
                if inserted:
                    code = candidate
                    break

        record = UrlRecord(code=code, url=submitted_url, created_at=created_at, click_count=0)
        base_url = normalized_public_base_url or str(request.base_url).rstrip("/")
        return JSONResponse(
            status_code=201,
            content=to_create_payload(record=record, short_url=f"{base_url}/{code}"),
        )

    @app.get("/{code}/stats")
    def code_stats(code: str) -> JSONResponse:
        record = repository.get(code)
        if record is None:
            return _error_response(
                status_code=404,
                code="NOT_FOUND",
                message="code not found",
                field="code",
            )
        return JSONResponse(status_code=200, content=to_stats_payload(record))

    @app.get("/{code}")
    def redirect(code: str):
        url = repository.increment_click_count_and_get_url(code)
        if url is None:
            return _error_response(
                status_code=404,
                code="NOT_FOUND",
                message="code not found",
                field="code",
            )
        return RedirectResponse(url=url, status_code=302)

    return app


app = create_app()
