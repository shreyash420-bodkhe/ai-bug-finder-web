from __future__ import annotations

import sqlite3
import sys
import types

from auth_manager import AuthStore
from database import HistoryStore


class _PostgresConnection:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = lambda cursor, row: {
            column[0]: row[index] for index, column in enumerate(cursor.description)
        }

    def execute(self, query, parameters=()):
        if "information_schema.columns" in query:
            cursor = self.connection.execute("PRAGMA table_info(analyses)")
            return _ColumnRows(cursor.fetchall())
        return self.connection.execute(query.replace("%s", "?"), parameters)

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()


class _ColumnRows:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return [{"column_name": row["name"]} for row in self.rows]


def test_auth_and_history_use_shared_database_url(tmp_path, monkeypatch):
    database_path = tmp_path / "shared-test-database.db"
    monkeypatch.setenv("DATABASE_URL", f"postgresql://test/{database_path.as_posix()}")
    monkeypatch.delenv("BUGFINDER_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BUGFINDER_ADMIN_PASSWORD", raising=False)

    psycopg = types.ModuleType("psycopg")
    psycopg.IntegrityError = sqlite3.IntegrityError
    psycopg.connect = lambda _url, row_factory=None: _PostgresConnection(database_path)
    psycopg_rows = types.ModuleType("psycopg.rows")
    psycopg_rows.dict_row = object()
    monkeypatch.setitem(sys.modules, "psycopg", psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", psycopg_rows)

    auth = AuthStore()
    history = HistoryStore()
    assert auth.register_user("person@example.com", "secure-password") == "registered"
    assert auth.validate_login("person@example.com", "secure-password") == (True, "user")

    record = history.add(
        "person@example.com",
        "sample.py",
        "print('hello')",
        {"summary": {"total": 0}, "issues": [], "fixed_code": "print('fixed')"},
    )
    assert record["fixed_code"] == "print('fixed')"
    assert history.list_for_user("person@example.com") == [record]
    assert history.list_all() == [record]
