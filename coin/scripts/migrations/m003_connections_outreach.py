#!/usr/bin/env python
"""Migration 003 — connections + outreach tables for /coin network-scan
(2026-04-25).

Creates the two tables previously created ad-hoc by
scripts/import_linkedin_connections.py. The importer still calls
ensure_schema() for backward-compat (and for fresh DBs that haven't run
migrations), but new pipelines should run this migration explicitly so
schema changes are tracked in `schema_migrations`.

Idempotent. Safe to re-run.

Usage:
  python scripts/migrations/m003_connections_outreach.py
  python scripts/migrations/m003_connections_outreach.py --dry-run
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "003_connections_outreach"

DDL = """
CREATE TABLE IF NOT EXISTS connections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT,
    last_name       TEXT,
    full_name       TEXT,
    linkedin_url    TEXT UNIQUE,
    email           TEXT,
    company         TEXT,
    company_normalized TEXT,
    position        TEXT,
    connected_on    DATE,
    seniority       TEXT,
    last_seen       DATE,
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_connections_company ON connections(company_normalized);
CREATE INDEX IF NOT EXISTS idx_connections_seniority ON connections(seniority);

CREATE TABLE IF NOT EXISTS outreach (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id         INTEGER REFERENCES roles(id),
    connection_id   INTEGER REFERENCES connections(id),
    drafted_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at         TIMESTAMP NULL,
    replied_at      TIMESTAMP NULL,
    warmth_score    REAL,
    draft_message   TEXT,
    notes           TEXT
);
CREATE INDEX IF NOT EXISTS idx_outreach_role ON outreach(role_id);
CREATE INDEX IF NOT EXISTS idx_outreach_connection ON outreach(connection_id);
"""


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


def apply(db_path: str | Path) -> None:
    """Public entrypoint — also used by tests against a temp DB."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_migrations_table(conn)
        if _already_applied(conn):
            return
        conn.executescript(DDL)
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))",
            (MIGRATION_ID,),
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db_path = ROOT / DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        conn = sqlite3.connect(str(db_path))
        try:
            _ensure_migrations_table(conn)
            if _already_applied(conn):
                print(f"Migration {MIGRATION_ID} already applied — would skip.")
                return 0
            print(f"[DRY RUN] Would apply DDL:\n{DDL}")
            return 0
        finally:
            conn.close()

    apply(db_path)
    print(f"✅ Migration {MIGRATION_ID} applied (or already in place).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
