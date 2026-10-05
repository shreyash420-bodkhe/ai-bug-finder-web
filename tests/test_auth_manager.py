from __future__ import annotations

import sqlite3

from auth_manager import AuthStore


def test_user_registration_and_login_use_sqlite(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    store = AuthStore(tmp_path / "users.db")

    assert store.register_user("Person@example.com", "secure-password") == "registered"
    assert store.validate_login("person@example.com", "secure-password") == (True, "user")
    assert store.validate_login("person@example.com", "wrong-password") == (False, None)


def test_admin_login_requires_configured_credentials(tmp_path, monkeypatch):
    monkeypatch.delenv("BUGFINDER_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BUGFINDER_ADMIN_PASSWORD", raising=False)
    store = AuthStore(tmp_path / "users.db")

    assert store.validate_login("admin@example.com", "any-password") == (False, None)

    monkeypatch.setenv("BUGFINDER_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("BUGFINDER_ADMIN_PASSWORD", "a-long-admin-password")
    assert store.validate_login("ADMIN@example.com", "a-long-admin-password") == (True, "admin")
    assert store.register_user("admin@example.com", "user-password") == "reserved_email"


def test_duplicate_registration_and_password_reset(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    store = AuthStore(tmp_path / "users.db")
    assert store.register_user("person@example.com", "old-password") == "registered"
    assert store.register_user("PERSON@example.com", "another-password") == "already_registered"
    assert store.reset_user_password("person@example.com", "new-password") == "updated"
    assert store.validate_login("person@example.com", "old-password") == (False, None)
    assert store.validate_login("person@example.com", "new-password") == (True, "user")

    with sqlite3.connect(tmp_path / "users.db") as connection:
        password_hash, = connection.execute(
            "SELECT password_hash FROM users WHERE email = ?", ("person@example.com",)
        ).fetchone()
    assert password_hash != "new-password"
