from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from url_shortener.models import UrlRecord


class UrlRepository:
    def __init__(self, db_path: str | Path):
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self._db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._lock:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS urls (
                    code TEXT PRIMARY KEY NOT NULL,
                    url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    click_count INTEGER NOT NULL DEFAULT 0 CHECK(click_count >= 0)
                )
                """
            )
            self._connection.commit()

    def insert(self, code: str, url: str, created_at: str) -> bool:
        with self._lock:
            try:
                self._connection.execute(
                    "INSERT INTO urls (code, url, created_at, click_count) VALUES (?, ?, ?, 0)",
                    (code, url, created_at),
                )
            except sqlite3.IntegrityError:
                self._connection.rollback()
                return False

            self._connection.commit()
            return True

    def get(self, code: str) -> UrlRecord | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT code, url, created_at, click_count FROM urls WHERE code = ?",
                (code,),
            ).fetchone()

        if row is None:
            return None

        return UrlRecord(
            code=row["code"],
            url=row["url"],
            created_at=row["created_at"],
            click_count=row["click_count"],
        )

    def increment_click_count_and_get_url(self, code: str) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT url FROM urls WHERE code = ?",
                (code,),
            ).fetchone()
            if row is None:
                return None

            self._connection.execute(
                "UPDATE urls SET click_count = click_count + 1 WHERE code = ?",
                (code,),
            )
            self._connection.commit()
            return row["url"]
