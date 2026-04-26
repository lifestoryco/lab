#!/usr/bin/env python
"""Migration 006 — bulk-load Lightcast Open Skills subset (2026-04-25).

Loads `data/skills/lightcast_subset.csv` (~560 skills curated to Sean's
4 lanes: TPM, SE/SA, IoT/wireless, RevOps) into the `skill` table.

The CSV columns: name, lightcast_id, category, slug.
- lightcast_id is NULL for now; can be backfilled when Sean signs up
  for a Lightcast account (which gives access to the official 34K-skill
  taxonomy + skill IDs).
- slug is the canonical lookup key (lowercase, hyphenated).
- name is the display form.
- category groups for the score panel + filtering.

Bootstraps m005 inline if applied to a fresh DB.

Idempotent: re-running upserts on slug. CSV updates (renames, new skills,
recategorizations) flow through cleanly.
"""

from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "006_seed_lightcast"
CSV_PATH = ROOT / "data" / "skills" / "lightcast_subset.csv"


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


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Lightcast subset CSV missing: {path}")
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Lightcast subset CSV empty: {path}")
    return rows


def _upsert_skills(conn: sqlite3.Connection, rows: list[dict[str, str]]) -> int:
    """Upsert by slug. Returns row count touched (insert + update)."""
    n = 0
    for row in rows:
        name = (row.get("name") or "").strip()
        slug = (row.get("slug") or "").strip()
        category = (row.get("category") or "").strip() or None
        lightcast_id = (row.get("lightcast_id") or "").strip() or None
        if not name or not slug:
            continue
        conn.execute(
            """
            INSERT INTO skill (name, lightcast_id, category, slug)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name = excluded.name,
                lightcast_id = COALESCE(excluded.lightcast_id, skill.lightcast_id),
                category = excluded.category
            """,
            (name, lightcast_id, category, slug),
        )
        n += 1
    return n


def apply(db_path: str | Path, csv_path: Path | None = None) -> int:
    """Public entrypoint — also used by tests against a temp DB.

    Returns the number of skill rows touched (insert+update).
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path = csv_path or CSV_PATH

    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_migrations_table(conn)
        if _already_applied(conn):
            return 0
        if not _table_exists(conn, "skill"):
            from scripts.migrations import m005_experience_db as m005
            m005.apply(db_path)
            conn.close()
            conn = sqlite3.connect(str(db_path))
        rows = _load_csv(csv_path)
        n = _upsert_skills(conn, rows)
        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))",
            (MIGRATION_ID,),
        )
        conn.commit()
        return n
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db_path = ROOT / DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        rows = _load_csv(CSV_PATH)
        print(f"[DRY RUN] Would upsert {len(rows)} skills from {CSV_PATH}")
        return 0

    n = apply(db_path)
    print(f"✅ Migration {MIGRATION_ID} applied — {n} skills loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
