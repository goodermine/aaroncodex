"""Durable state for the Singnexa beta: users, sessions and jobs in SQLite.

Stdlib only. Passwords are scrypt-hashed; session tokens are random and only
their SHA-256 is stored, so a copied database cannot be replayed as a login.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from pathlib import Path

SESSION_SECONDS = 30 * 24 * 60 * 60
USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{1,31}$")
MIN_PASSWORD = 10

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2 ** 14, 8, 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    disabled INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status TEXT NOT NULL,
    stage TEXT NOT NULL,
    song TEXT NOT NULL DEFAULT '',
    artist TEXT NOT NULL DEFAULT '',
    capture TEXT NOT NULL DEFAULT '',
    intent TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    original_filename TEXT NOT NULL DEFAULT '',
    size_bytes INTEGER NOT NULL DEFAULT 0,
    duration_s REAL,
    overall REAL,
    capture_fair REAL,
    confidence TEXT,
    error_code TEXT,
    error_reason TEXT,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_by_user ON jobs(user_id, created_at);
"""

JOB_FIELDS = ("id", "user_id", "status", "stage", "song", "artist", "capture", "intent",
              "note", "original_filename", "size_bytes", "duration_s", "overall",
              "capture_fair", "confidence", "error_code", "error_reason",
              "created_at", "updated_at")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R,
                            p=_SCRYPT_P, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${b64(salt)}${b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode("utf-8"), salt=base64.b64decode(salt),
                                n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def temporary_password() -> str:
    """Readable one-time password: four groups, no look-alike characters."""
    alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4))


def password_problem(password: str) -> str | None:
    if len(password or "") < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if len(password) > 256:
        return "That password is too long."
    return None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(self.path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.executescript(SCHEMA)
            self._db.commit()

    def _run(self, sql: str, args: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._db.execute(sql, args)
            self._db.commit()
            return cur

    def _one(self, sql: str, args: tuple = ()) -> dict | None:
        with self._lock:
            row = self._db.execute(sql, args).fetchone()
        return dict(row) if row else None

    def _all(self, sql: str, args: tuple = ()) -> list[dict]:
        with self._lock:
            return [dict(r) for r in self._db.execute(sql, args).fetchall()]

    # ---- users ----------------------------------------------------------
    def create_user(self, username: str, display_name: str = "", is_admin: bool = False,
                    password: str | None = None) -> tuple[dict, str]:
        """Create a user. Returns (user, one-time password). The user must
        change the password at first sign-in unless one was supplied."""
        username = (username or "").strip().lower()
        if not USERNAME_RE.match(username):
            raise ValueError("Usernames are 2-32 characters: lower-case letters, digits, '.', '_' or '-'.")
        if self.user_by_username(username):
            raise ValueError("That username is taken.")
        chosen = password or temporary_password()
        if password and password_problem(password):
            raise ValueError(password_problem(password))
        display = " ".join((display_name or username).split())[:80] or username
        self._run("INSERT INTO users (username, display_name, password_hash, is_admin, "
                  "must_change_password, created_at) VALUES (?,?,?,?,?,?)",
                  (username, display, hash_password(chosen), int(is_admin),
                   0 if password else 1, time.time()))
        return self.user_by_username(username), chosen

    def user_by_username(self, username: str) -> dict | None:
        return self._one("SELECT * FROM users WHERE username = ?", ((username or "").strip().lower(),))

    def user_by_id(self, user_id: int) -> dict | None:
        return self._one("SELECT * FROM users WHERE id = ?", (user_id,))

    def list_users(self) -> list[dict]:
        return self._all(
            "SELECT u.id, u.username, u.display_name, u.is_admin, u.must_change_password, "
            "u.disabled, u.created_at, (SELECT COUNT(*) FROM jobs j WHERE j.user_id = u.id) AS jobs "
            "FROM users u ORDER BY u.created_at")

    def authenticate(self, username: str, password: str) -> dict | None:
        user = self.user_by_username(username)
        if not user:
            verify_password(password, hash_password("timing-equaliser"))
            return None
        if not verify_password(password, user["password_hash"]) or user["disabled"]:
            return None
        return user

    def set_password(self, user_id: int, password: str, must_change: bool = False) -> None:
        problem = password_problem(password)
        if problem:
            raise ValueError(problem)
        self._run("UPDATE users SET password_hash = ?, must_change_password = ? WHERE id = ?",
                  (hash_password(password), int(must_change), user_id))

    def reset_password(self, user_id: int) -> str:
        """New one-time password; signs the user out everywhere."""
        chosen = temporary_password()
        self._run("UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
                  (hash_password(chosen), user_id))
        self.end_sessions(user_id)
        return chosen

    def set_disabled(self, user_id: int, disabled: bool) -> None:
        self._run("UPDATE users SET disabled = ? WHERE id = ?", (int(disabled), user_id))
        if disabled:
            self.end_sessions(user_id)

    # ---- sessions -------------------------------------------------------
    def start_session(self, user_id: int) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        self._run("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?,?,?,?)",
                  (_token_hash(token), user_id, now, now + SESSION_SECONDS))
        self._run("DELETE FROM sessions WHERE expires_at < ?", (now,))
        return token

    def session_user(self, token: str | None) -> dict | None:
        if not token:
            return None
        row = self._one("SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
                        "WHERE s.token_hash = ? AND s.expires_at > ? AND u.disabled = 0",
                        (_token_hash(token), time.time()))
        return row

    def end_session(self, token: str | None) -> None:
        if token:
            self._run("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))

    def end_sessions(self, user_id: int, keep: str | None = None) -> None:
        if keep:
            self._run("DELETE FROM sessions WHERE user_id = ? AND token_hash != ?", (user_id, _token_hash(keep)))
        else:
            self._run("DELETE FROM sessions WHERE user_id = ?", (user_id,))

    # ---- jobs -----------------------------------------------------------
    def create_job(self, job_id: str, user_id: int, **fields) -> dict:
        now = time.time()
        row = {"id": job_id, "user_id": user_id, "status": "queued", "stage": "queued",
               "created_at": now, "updated_at": now}
        row.update({k: v for k, v in fields.items() if k in JOB_FIELDS})
        cols = ", ".join(row)
        self._run(f"INSERT INTO jobs ({cols}) VALUES ({', '.join('?' for _ in row)})", tuple(row.values()))
        return self.job(job_id)

    def update_job(self, job_id: str, **fields) -> None:
        fields = {k: v for k, v in fields.items() if k in JOB_FIELDS and k not in ("id", "user_id")}
        fields["updated_at"] = time.time()
        sets = ", ".join(f"{k} = ?" for k in fields)
        self._run(f"UPDATE jobs SET {sets} WHERE id = ?", (*fields.values(), job_id))

    def job(self, job_id: str) -> dict | None:
        return self._one("SELECT * FROM jobs WHERE id = ?", (job_id,))

    def jobs_for(self, user_id: int | None = None, limit: int = 200) -> list[dict]:
        if user_id is None:
            return self._all("SELECT j.*, u.username, u.display_name FROM jobs j JOIN users u ON u.id = j.user_id "
                             "ORDER BY j.created_at DESC LIMIT ?", (limit,))
        return self._all("SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))

    def active_jobs(self, user_id: int | None = None) -> int:
        if user_id is None:
            row = self._one("SELECT COUNT(*) AS n FROM jobs WHERE status IN ('queued','processing')")
        else:
            row = self._one("SELECT COUNT(*) AS n FROM jobs WHERE user_id = ? AND status IN ('queued','processing')",
                            (user_id,))
        return int(row["n"])

    def jobs_since(self, user_id: int, since: float) -> int:
        row = self._one("SELECT COUNT(*) AS n FROM jobs WHERE user_id = ? AND created_at >= ?", (user_id, since))
        return int(row["n"])

    def interrupted_jobs(self) -> list[dict]:
        return self._all("SELECT * FROM jobs WHERE status IN ('queued','processing')")

    def delete_job(self, job_id: str) -> None:
        self._run("DELETE FROM jobs WHERE id = ?", (job_id,))
