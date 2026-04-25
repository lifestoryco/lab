#!/usr/bin/env python
"""Migration 001 — 5 archetypes → 4 (2026-04-25).

Idempotent. Rerunning is safe; rows already at the target lane name are
no-ops. Tracks applied state in `schema_migrations` table.

Lane rename map:
  cox-style-tpm                → mid-market-tpm
  titanx-style-pm              → out_of_band         (FAANG-flavored PM)
  global-eng-orchestrator      → iot-solutions-architect
  revenue-ops-transformation   → revenue-ops-operator
  enterprise-sales-engineer    → enterprise-sales-engineer (no change)

Quarantine guarantee: any row landing in `out_of_band` after this migration
gets fit_score=0 to preserve the pedigree-filter sink.

Usage:
  python scripts/migrations/001_archetypes_5_to_4.py
  python scripts/migrations/001_archetypes_5_to_4.py --dry-run
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "001_archetypes_5_to_4"

LANE_MAP = {
    "cox-style-tpm": "mid-market-tpm",
    "titanx-style-pm": "out_of_band",
    "global-eng-orchestrator": "iot-solutions-architect",
    "revenue-ops-transformation": "revenue-ops-operator",
}


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Report changes without applying")
    args = ap.parse_args()

    db_path = ROOT / DB_PATH
    if not db_path.exists():
        print(f"DB does not exist at {db_path}; nothing to migrate.")
        return 0

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _ensure_migrations_table(conn)

    if _already_applied(conn) and not args.dry_run:
        print(f"Migration {MIGRATION_ID} already applied. Skipping.")
        conn.close()
        return 0

    # Report pre-state
    pre = {
        row["lane"]: row["count"]
        for row in conn.execute("SELECT lane, COUNT(*) AS count FROM roles GROUP BY lane")
    }
    print("Lane distribution BEFORE:")
    for lane, count in sorted(pre.items()):
        print(f"  {lane:32s} {count}")

    if args.dry_run:
        print("\n[DRY RUN] Would apply:")
        for old, new in LANE_MAP.items():
            count = pre.get(old, 0)
            if count:
                print(f"  {old} → {new}  ({count} rows)")
        conn.close()
        return 0

    # Apply
    print("\nApplying migration:")
    for old, new in LANE_MAP.items():
        cur = conn.execute("UPDATE roles SET lane = ? WHERE lane = ?", (new, old))
        if cur.rowcount:
            print(f"  {old} → {new}  ({cur.rowcount} rows)")
    # Force quarantine sink: any row in out_of_band gets fit_score=0
    cur = conn.execute("UPDATE roles SET fit_score = 0 WHERE lane = 'out_of_band'")
    if cur.rowcount:
        print(f"  Quarantine sink applied: {cur.rowcount} rows zeroed")

    conn.execute(
        "INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))",
        (MIGRATION_ID,),
    )
    conn.commit()

    # Report post-state
    post = {
        row["lane"]: row["count"]
        for row in conn.execute("SELECT lane, COUNT(*) AS count FROM roles GROUP BY lane")
    }
    print("\nLane distribution AFTER:")
    for lane, count in sorted(post.items()):
        print(f"  {lane:32s} {count}")
    conn.close()
    print(f"\n✅ Migration {MIGRATION_ID} applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
