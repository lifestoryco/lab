#!/usr/bin/env python
"""Migration 002 — offers table for /coin ofertas (2026-04-25).

Creates the `offers` table for multi-offer comparison + negotiation math.
Idempotent. Tracks applied state in `schema_migrations`.

Columns capture the dimensions ofertas needs for Y1 / 3-yr TC math:
  base, signing, RSU grant + vesting curve, bonus target + historical hit-rate,
  benefits delta, PTO, remote %, state (for tax), growth signal, expiration.

Usage:
  python scripts/migrations/002_offers_table.py
  python scripts/migrations/002_offers_table.py --dry-run
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "002_offers_table"

DDL = """
CREATE TABLE IF NOT EXISTS offers (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id                  INTEGER REFERENCES roles(id),
    company                  TEXT NOT NULL,
    title                    TEXT NOT NULL,
    received_at              DATE NOT NULL,
    expires_at               DATE,
    base_salary              INTEGER NOT NULL,
    signing_bonus            INTEGER DEFAULT 0,
    annual_bonus_target_pct  REAL DEFAULT 0,
    annual_bonus_paid_history TEXT,
    rsu_total_value          INTEGER DEFAULT 0,
    rsu_vesting_schedule     TEXT,
    rsu_vest_years           INTEGER DEFAULT 4,
    rsu_cliff_months         INTEGER DEFAULT 12,
    equity_refresh_expected  INTEGER DEFAULT 0,
    benefits_delta           INTEGER DEFAULT 0,
    pto_days                 INTEGER,
    remote_pct               INTEGER,
    state_tax                TEXT,
    growth_signal            TEXT,
    notes                    TEXT,
    status                   TEXT DEFAULT 'active',
    created_at               TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_offers_role ON offers(role_id);
CREATE INDEX IF NOT EXISTS idx_offers_status ON offers(status);
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

    conn = sqlite3.connect(str(db_path))
    _ensure_migrations_table(conn)
    if _already_applied(conn):
        print(f"Migration {MIGRATION_ID} already applied. Skipping.")
        conn.close()
        return 0

    if args.dry_run:
        print(f"[DRY RUN] Would apply DDL:\n{DDL}")
        conn.close()
        return 0

    conn.executescript(DDL)
    conn.execute(
        "INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))",
        (MIGRATION_ID,),
    )
    conn.commit()
    conn.close()
    print(f"✅ Migration {MIGRATION_ID} applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
