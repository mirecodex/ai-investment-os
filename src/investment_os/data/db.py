"""SQLite connection + forward-only migrations.

SQLite keeps Tahap 0 deployable anywhere with zero infrastructure; the store
classes speak plain SQL through this thin wrapper, so a Postgres variant is a
new module implementing the same ports — not a refactor. Access is serialized
with a lock: correctness first, connection pooling when a real load profile
exists.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from investment_os.observability import get_logger

log = get_logger(__name__)

MIGRATIONS: tuple[str, ...] = (
    """
    CREATE TABLE users (
        user_id    TEXT PRIMARY KEY,
        created_at TEXT NOT NULL
    );
    CREATE TABLE watchlist (
        user_id    TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        ticker     TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (user_id, ticker)
    );
    CREATE TABLE recommendations (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id           TEXT NOT NULL,
        ticker           TEXT NOT NULL,
        company          TEXT NOT NULL,
        sector           TEXT NOT NULL,
        verdict          TEXT NOT NULL,
        proposed_verdict TEXT NOT NULL,
        confidence       REAL NOT NULL,
        confidence_band  TEXT NOT NULL,
        requires_review  INTEGER NOT NULL,
        headline         TEXT NOT NULL,
        reasons_json     TEXT NOT NULL,
        factors_json     TEXT NOT NULL,
        audit_json       TEXT NOT NULL,
        engine_version   TEXT NOT NULL,
        as_of            TEXT NOT NULL,
        created_at       TEXT NOT NULL
    );
    CREATE INDEX idx_recommendations_ticker
        ON recommendations(ticker, created_at DESC);
    CREATE TABLE evidence_refs (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_id       INTEGER NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
        source       TEXT NOT NULL,
        ref_id       TEXT NOT NULL,
        summary      TEXT NOT NULL,
        published_at TEXT NOT NULL,
        reliability  REAL NOT NULL,
        url          TEXT
    );
    CREATE TABLE rule_triggers (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_id  INTEGER NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
        rule_id TEXT NOT NULL,
        effect  TEXT NOT NULL,
        reason  TEXT NOT NULL
    );
    CREATE TABLE outcomes (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        rec_id        INTEGER NOT NULL REFERENCES recommendations(id) ON DELETE CASCADE,
        horizon       TEXT NOT NULL,
        actual_return REAL NOT NULL,
        evaluated_at  TEXT NOT NULL,
        UNIQUE (rec_id, horizon)
    );
    """,
    """
    CREATE TABLE subscriptions (
        user_id    TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
        chat_id    INTEGER NOT NULL,
        created_at TEXT NOT NULL
    );
    """,
)


class Database:
    def __init__(self, path: Path | str) -> None:
        if isinstance(path, str) and path != ":memory:":
            path = Path(path)
        if isinstance(path, Path):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self.transaction() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA foreign_keys = ON")
        self._migrate()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def close(self) -> None:
        self._conn.close()

    def _migrate(self) -> None:
        with self.transaction() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
            row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
            current = row["v"] or 0
            for version, script in enumerate(MIGRATIONS[current:], start=current + 1):
                conn.executescript(script)
                conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
                log.info("db_migrated", version=version)
