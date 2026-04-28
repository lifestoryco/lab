#!/usr/bin/env python
"""Migration 008 — two-stage scoring columns (2026-04-28).

Adds four columns to `roles` that support the COIN-SCORE-V2 two-stage
discovery pipeline:

  score_stage1  REAL    — title + company-tier score (JD-blind, stage 1)
  score_stage2  REAL    — full JD-aware + DQ-aware score (NULL until stage 2 runs)
  score_stage   INTEGER — 1 or 2; which stage is currently authoritative
  jd_parsed_at  TEXT    — ISO timestamp of the last stage-2 parse

Backfill: existing `fit_score` values are copied to `score_stage1` so
pre-migration rows participate in `get_top_n_for_deep_score`.

`fit_score` column is preserved unchanged for backward compat.

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

MIGRATION_ID = "m008_two_stage_score"

ROLES_COLUMNS_NO_STAGE = [
    "id", "url", "title", "company", "location", "remote", "lane",
    "comp_min", "comp_max", "comp_source", "comp_currency", "comp_confidence",
    "fit_score", "status", "source", "jd_raw", "jd_parsed", "notes",
    "discovered_at", "posted_at", "updated_at", "jd_parsed_at",
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
    from scripts.migrations import (
        m001_archetypes_5_to_4 as m001,
        m002_offers_table as m002,
        m003_connections_outreach as m003,
        m004_outreach_role_tag as m004,
        m005_posted_at as m005,
        m006_comp_currency as m006,
        m007_comp_confidence as m007,
    )
    for mod in (m001, m002, m003, m004, m005, m006, m007):
        if hasattr(mod, "apply"):
            try:
                mod.apply(db_path)
            except Exception:
                pass


def apply(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_migrations_table(conn)
        if _already_applied(conn):
            return
        if not _table_exists(conn, "roles"):
            conn.close()
            _bootstrap_prior(db_path)
            from careerops import pipeline
            pipeline.init_db()
            conn = sqlite3.connect(str(db_path))
            _ensure_migrations_table(conn)

        new_cols = [
            ("score_stage1", "REAL"),
            ("score_stage2", "REAL"),
            ("score_stage",  "INTEGER DEFAULT 1"),
            ("jd_parsed_at", "TEXT"),
        ]
        for col, col_type in new_cols:
            if not _has_column(conn, "roles", col):
                conn.execute(f"ALTER TABLE roles ADD COLUMN {col} {col_type}")

        # Backfill: copy existing fit_score → score_stage1 where not already set
        if _has_column(conn, "roles", "fit_score"):
            conn.execute(
                "UPDATE roles SET score_stage1 = fit_score "
                "WHERE fit_score IS NOT NULL AND score_stage1 IS NULL"
            )

        conn.execute(
            "INSERT INTO schema_migrations (id, applied_at) VALUES (?, datetime('now'))",
            (MIGRATION_ID,),
        )
        conn.commit()
    finally:
        conn.close()


def rollback(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        _ensure_migrations_table(conn)
        stage_cols = ["score_stage1", "score_stage2", "score_stage"]
        any_present = any(_has_column(conn, "roles", c) for c in stage_cols)
        if not any_present:
            conn.execute("DELETE FROM schema_migrations WHERE id = ?", (MIGRATION_ID,))
            conn.commit()
            return
        if sqlite3.sqlite_version_info >= (3, 35, 0):
            for col in stage_cols:
                if _has_column(conn, "roles", col):
                    conn.execute(f"ALTER TABLE roles DROP COLUMN {col}")
        else:
            # Rebuild table without stage columns (keep jd_parsed_at — other code uses it)
            cols = ", ".join(ROLES_COLUMNS_NO_STAGE)
            conn.execute("""
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
                    comp_currency TEXT DEFAULT 'USD',
                    comp_confidence REAL,
                    fit_score     REAL,
                    status        TEXT DEFAULT 'discovered',
                    source        TEXT,
                    jd_raw        TEXT,
                    jd_parsed     TEXT,
                    notes         TEXT,
                    discovered_at TEXT,
                    posted_at     TEXT,
                    updated_at    TEXT,
                    jd_parsed_at  TEXT
                )
            """)
            conn.execute(f"INSERT INTO roles_new ({cols}) SELECT {cols} FROM roles")
            conn.execute("DROP TABLE roles")
            conn.execute("ALTER TABLE roles_new RENAME TO roles")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_status ON roles(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_lane   ON roles(lane)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_roles_fit    ON roles(fit_score)")
        conn.execute("DELETE FROM schema_migrations WHERE id = ?", (MIGRATION_ID,))
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rollback", action="store_true")
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
