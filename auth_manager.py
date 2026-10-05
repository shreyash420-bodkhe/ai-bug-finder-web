from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class AuthStore:
    """Persist registered email accounts without storing plaintext passwords."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path(__file__).with_name("database") / "users.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY COLLATE NOCASE,
                    password_salt TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    @contextmanager
    def _session(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @property
    def admin_email(self) -> str:
        return os.getenv("BUGFINDER_ADMIN_EMAIL", "").strip().lower()

    @property
    def admin_password(self) -> str:
        return os.getenv("BUGFINDER_ADMIN_PASSWORD", "")

    @staticmethod
    def _password_hash(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000).hex()

    def register_user(self, email: str, password: str) -> str:
        cleaned_email = (email or "").strip().lower()
        cleaned_password = password or ""
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned_email):
            return "invalid_email"
        if cleaned_email == self.admin_email:
            return "reserved_email"
        if len(cleaned_password) < 8:
            return "weak_password"

        salt = secrets.token_bytes(16)
        try:
            with self._session() as connection:
                connection.execute(
                    "INSERT INTO users (email, password_salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (
                        cleaned_email,
                        salt.hex(),
                        self._password_hash(cleaned_password, salt),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        except sqlite3.IntegrityError:
            return "already_registered"
        return "registered"

    def validate_login(self, email: str, password: str) -> tuple[bool, str | None]:
        cleaned_email = (email or "").strip().lower()
        cleaned_password = password or ""
        if not cleaned_email or not cleaned_password:
            return False, None

        admin_email = self.admin_email
        admin_password = self.admin_password
        if admin_email and admin_password and hmac.compare_digest(cleaned_email, admin_email):
            if hmac.compare_digest(cleaned_password, admin_password):
                return True, "admin"
            return False, None

        with self._session() as connection:
            user = connection.execute(
                "SELECT password_salt, password_hash FROM users WHERE email = ?",
                (cleaned_email,),
            ).fetchone()
        if user is None:
            return False, None

        salt = bytes.fromhex(user["password_salt"])
        password_hash = self._password_hash(cleaned_password, salt)
        if hmac.compare_digest(password_hash, user["password_hash"]):
            return True, "user"
        return False, None

    def reset_user_password(self, email: str, new_password: str) -> str:
        """Set a registered user's password without exposing or storing plaintext."""
        cleaned_email = (email or "").strip().lower()
        cleaned_password = new_password or ""
        if cleaned_email == self.admin_email:
            return "reserved_email"
        if len(cleaned_password) < 8:
            return "weak_password"

        salt = secrets.token_bytes(16)
        with self._session() as connection:
            cursor = connection.execute(
                "UPDATE users SET password_salt = ?, password_hash = ? WHERE email = ?",
                (salt.hex(), self._password_hash(cleaned_password, salt), cleaned_email),
            )
        return "updated" if cursor.rowcount else "not_found"

    def list_users(self) -> list[dict[str, str]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT email, created_at FROM users ORDER BY created_at ASC"
            ).fetchall()
        return [{"email": row["email"], "created_at": row["created_at"]} for row in rows]


def validate_login(
    email: str,
    password: str,
    database_path: str | Path | None = None,
) -> tuple[bool, str | None]:
    return AuthStore(database_path).validate_login(email, password)
