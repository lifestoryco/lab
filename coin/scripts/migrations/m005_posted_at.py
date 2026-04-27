#!/usr/bin/env python
"""Migration 005 — roles.posted_at (2026-04-27).

Adds `posted_at TEXT` column to `roles` so we can capture and surface
the LinkedIn posting age. Without this, every role's `discovered_at`
just records when Coin first saw it, which masks stale month-old
postings (the Filevine SE motivating example: posting was ~30 days
old but looked fresh in the dashboard).

Idempotent. Supports `--rollback` (drops the column on SQLite ≥3.35,
otherwise rebuilds the table).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "m005_posted_at"

# Column list MINUS posted_at — used by the rollback path on SQLite <3.35
# to rebuild the table. Must mirror the CREATE TABLE in pipeline.init_db.
ROLES_COLUMNS_NO_POSTED_AT = [
    "id", "url", "title", "company", "location", "remote", "lane",
    "comp_min", "comp_max", "comp_source", "fit_score", "status",
    "source", "jd_raw", "jd_parsed", "notes", "discovered_at", "updated_at",
]


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id          TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL
        )
    """)


def _already_applied(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM schema_migrations WHERE id = ?", (MIGRATION_ID,)
    ).fetchone()
    return row is not None


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _bootstrap_prior(db_path: str | Path) -> None:
    """Self-bootstrap m001..m004 on a fresh DB so this migration can run
    independently in tests / fresh installs."""
    from scripts.migrations import (
        m001_archetypes_5_to_4 as m001,
        m002_offers_table as m002,
        m003_connections_outreach as m003,
        m004_outreach_role_tag as m004,
    )
    # m001 may not have an apply() public (it's a one-shot data fix). Best
    # effort: call apply if present, else import is enough.
    for mod in (m001, m002, m003, m004):
        if hasattr(mod, "apply"):
            try:
                mod.apply(db_path)
            except Exception:
                # m001 is data-fix only; if it errors on a fresh DB that's OK.
                pass


def apply(db_path: str | Path) -> None:
    """Public entrypoint — also used by tests against a temp DB."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_migrations_table(conn)
        if _already_applied(conn):
            return
        if not _table_exists(conn, "roles"):
            # Bootstrap prior migrations + ensure roles table exists.
            conn.close()
            _bootstrap_prior(db_path)
            # Ensure roles table — pipeline.init_db creates it.
            from careerops import pipeline
            pipeline.init_db()
            conn = sqlite3.connect(str(db_path))
            _ensure_migrations_table(conn)
        if not _has_column(conn, "roles", "posted_at"):
            conn.execute("ALTER TABLE roles ADD COLUMN posted_at TEXT")
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))",
            (MIGRATION_ID,),
        )
        conn.commit()
    finally:
        conn.close()


def rollback(db_path: str | Path) -> None:
    """Reverse of apply(): drop posted_at and the schema_migrations row."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_migrations_table(conn)
        if not _has_column(conn, "roles", "posted_at"):
            conn.execute(
                "DELETE FROM schema_migrations WHERE id = ?", (MIGRATION_ID,)
            )
            conn.commit()
            return
        if sqlite3.sqlite_version_info >= (3, 35, 0):
            conn.execute("ALTER TABLE roles DROP COLUMN posted_at")
        else:
            # Rebuild the table without posted_at.
            cols = ", ".join(ROLES_COLUMNS_NO_POSTED_AT)
            conn.execute(f"""
                CREATE TABLE roles_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    url           TEXT UNIQUE NOT NULL,
                    title         TEXT,
                    company       TEXT,
                    location      TEXT,
                    remote        INTEGER DEFAULT 0,
                    lane          TEXT,
                    comp_min      INTEGER,
                    comp_max      INTEGER,
                    comp_source   TEXT,
                    fit_score     REAL,
                    status        TEXT DEFAULT 'discovered',
                    source        TEXT,
                    jd_raw        TEXT,
                    jd_parsed     TEXT,
                    notes         TEXT,
                    discovered_at TEXT,
                    updated_at    TEXT
                )
            """)
            conn.execute(f"INSERT INTO roles_new ({cols}) SELECT {cols} FROM roles")
            conn.execute("DROP TABLE roles")
            conn.execute("ALTER TABLE roles_new RENAME TO roles")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_status ON roles(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_lane   ON roles(lane)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_fit    ON roles(fit_score)")
        conn.execute(
            "DELETE FROM schema_migrations WHERE id = ?", (MIGRATION_ID,)
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollback", action="store_true", help="Revert the migration")
    args = ap.parse_args()

    db_path = ROOT / DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.rollback:
        rollback(db_path)
        print(f"Migration {MIGRATION_ID} rolled back.")
        return 0

    apply(db_path)
    print(f"Migration {MIGRATION_ID} applied (or already in place).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
