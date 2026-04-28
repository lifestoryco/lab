#!/usr/bin/env python
"""Migration 009 — notified_at column for COIN-SCHEDULER (2026-04-28).

Adds one column to `roles`:

  notified_at  TEXT NULL  — ISO timestamp of the last successful iMessage
                            interrupt sent to Sean for this role. NULL =
                            never notified (eligible for next notify run).

Idempotent. Supports `--rollback`.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "m009_notified_at"


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def _ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id          TEXT PRIMARY KEY,
            applied_at  TEXT DEFAULT (datetime('now'))
        )
        """
    )


def apply(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema_migrations(conn)
        already = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE id = ?", (MIGRATION_ID,)
        ).fetchone()
        if already:
            return
        if not _has_column(conn, "roles", "notified_at"):
            conn.execute("ALTER TABLE roles ADD COLUMN notified_at TEXT")
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(id) VALUES (?)",
            (MIGRATION_ID,),
        )
        conn.commit()
    finally:
        conn.close()


def rollback(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema_migrations(conn)
        # SQLite >= 3.35 supports DROP COLUMN; older versions need a table rebuild.
        version_str = sqlite3.sqlite_version_info
        if version_str >= (3, 35, 0):
            if _has_column(conn, "roles", "notified_at"):
                conn.execute("ALTER TABLE roles DROP COLUMN notified_at")
        conn.execute(
            "DELETE FROM schema_migrations WHERE id = ?", (MIGRATION_ID,)
        )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollback", action="store_true")
    args = ap.parse_args()

    db_path = ROOT / DB_PATH if not Path(DB_PATH).is_absolute() else Path(DB_PATH)
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
