#!/usr/bin/env python
"""Migration 004 — outreach.contact_role + outreach.target_role_id (2026-04-25).

Adds two columns to `outreach` so a connection's relationship to a role can
be tagged. Used by:

- `modes/cover-letter.md` to auto-populate `recipient_name` when an outreach
  row marks a connection as the role's hiring manager.
- `modes/network-scan.md` to record (when Sean tags one) that a specific
  contact is the hiring manager for the role we're scanning for.

Idempotent. ALTER TABLE ADD COLUMN is safe because it always defaults to
NULL for existing rows. Re-running is a no-op (we check for the column
before adding).
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "004_outreach_role_tag"

# Allowed values for contact_role. Stored as TEXT — sqlite has no enum type
# but the helpers in careerops.pipeline (and modes/network-scan.md) MUST
# only write one of these. Keep this list in sync with documentation.
ALLOWED_CONTACT_ROLES = (
    "hiring_manager",
    "team_member",
    "recruiter",
    "exec_sponsor",
    "alumni_intro",
)


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


def apply(db_path: str | Path) -> None:
    """Public entrypoint — also used by tests against a temp DB."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_migrations_table(conn)
        if _already_applied(conn):
            return
        if not _table_exists(conn, "outreach"):
            # m003 must run first. Re-running m003 inline keeps the apply
            # function self-contained for fresh DBs.
            from scripts.migrations import m003_connections_outreach as m003
            m003.apply(db_path)
            # m003 closed its connection; reopen.
            conn.close()
            conn = sqlite3.connect(str(db_path))
        if not _has_column(conn, "outreach", "contact_role"):
            conn.execute("ALTER TABLE outreach ADD COLUMN contact_role TEXT")
        if not _has_column(conn, "outreach", "target_role_id"):
            # Mirrors role_id but explicit: target_role_id is the role we're
            # connecting *for* (always equal to role_id today, but kept
            # separate so a single contact can be tagged as hiring_manager
            # for multiple roles in the future without ambiguity).
            conn.execute("ALTER TABLE outreach ADD COLUMN target_role_id INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_outreach_contact_role "
            "ON outreach(role_id, contact_role)"
        )
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
            print(f"[DRY RUN] Would add outreach.contact_role + outreach.target_role_id")
            print(f"          + idx_outreach_contact_role")
            return 0
        finally:
            conn.close()

    apply(db_path)
    print(f"✅ Migration {MIGRATION_ID} applied (or already in place).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
