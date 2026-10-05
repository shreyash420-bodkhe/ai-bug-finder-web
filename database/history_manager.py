from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


class HistoryStore:
    """Store local analysis history and retrieve learning context per profile."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.database_url = os.getenv("DATABASE_URL")
        self.path = Path(path or Path(__file__).with_name("history.db"))
        if not self.database_url:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> Any:
        if self.database_url:
            try:
                import psycopg
                from psycopg.rows import dict_row
            except ImportError as error:
                raise RuntimeError("DATABASE_URL requires psycopg[binary].") from error
            return psycopg.connect(self.database_url, row_factory=dict_row)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _session(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, Any]:
        if isinstance(row, dict):
            return {
                "id": row["id"],
                "user": row["user_name"],
                "filename": row["filename"],
                "created_at": row["created_at"],
                "source": row["source"],
                "result": json.loads(row["result_json"]),
            }
        return {
            "id": row["id"],
            "user": row["user_name"],
            "filename": row["filename"],
            "created_at": row["created_at"],
            "source": row["source"],
            "result": json.loads(row["result_json"]),
        }

    def list_for_user(self, user: str) -> list[dict[str, Any]]:
        with self._session() as connection:
            placeholder = "%s" if self.database_url else "?"
            rows = connection.execute(
                f"SELECT * FROM analyses WHERE user_name = {placeholder} ORDER BY created_at ASC",
                (user,),
            ).fetchall()
        return [self._record(row) for row in rows]

    def list_all(self) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM analyses ORDER BY created_at ASC"
            ).fetchall()
        return [self._record(row) for row in rows]

    def add(
        self,
        user: str,
        filename: str,
        source: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        record = {
            "id": uuid4().hex,
            "user": user,
            "filename": filename,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "result": result,
        }
        with self._session() as connection:
            placeholder = "%s" if self.database_url else "?"
            connection.execute(
                f"INSERT INTO analyses (id, user_name, filename, created_at, source, result_json) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})",
                (
                    record["id"],
                    record["user"],
                    record["filename"],
                    record["created_at"],
                    record["source"],
                    json.dumps(record["result"]),
                ),
            )
        return record

    def learning_context(self, user: str, limit: int = 5) -> list[dict[str, Any]]:
        """Return recent findings and fixes without sending the full history by default."""
        records = self.list_for_user(user)[-limit:]
        return [
            {
                "filename": record["filename"],
                "summary": record["result"].get("summary", {}),
                "issues": record["result"].get("issues", []),
                "fixed_code": record["result"].get("fixed_code"),
            }
            for record in records
        ]

    def delete_for_user(self, user: str) -> None:
        with self._session() as connection:
            placeholder = "%s" if self.database_url else "?"
            connection.execute(f"DELETE FROM analyses WHERE user_name = {placeholder}", (user,))
