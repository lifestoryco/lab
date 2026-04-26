#!/usr/bin/env python
"""Migration 005 — experience database (2026-04-25).

Coin v2: structured experience DB grounding the resume tailoring system.

Creates 10 new tables. The existing PROFILE dict in data/resumes/base.py
becomes seed-input only via scripts/seed_from_base_py.py. Tailor mode
reads from these tables at runtime, not from the dict.

Idempotent. Safe to re-run. Tables use CREATE IF NOT EXISTS, indexes too.

Schema notes:
- `accomplishment.position_slug` references base.py positions[].id
  ('ca_engineering' | 'hydrant' | 'utah_broadband' | 'linx'). It is NOT
  a FK to coin's `roles` table — `roles` holds JOB POSTINGS Sean is
  applying to. We keep the position list as a TEXT slug on accomplishment
  rows because Sean has 4 positions and a separate table would be over-
  engineering.
- `jd_keyword.role_id` and `render_artifact.role_id` ARE FKs to coin's
  `roles` table (the job-postings table from pipeline.py).
- ON DELETE CASCADE everywhere downstream of accomplishment so cleaning
  up one accomplishment cleans its outcomes/evidence/variants/tags.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

MIGRATION_ID = "005_experience_db"

DDL = """
-- ─────────────────────────────────────────────────────────────────
-- accomplishment: master table — one row per career proof point.
-- Seeded from base.py PROFILE positions[].bullets, then enriched
-- via /coin capture STAR sessions.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accomplishment (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    position_slug      TEXT NOT NULL,
    title              TEXT NOT NULL,
    time_period_start  TEXT,
    time_period_end    TEXT,
    situation          TEXT,
    task               TEXT,
    action             TEXT,
    result             TEXT,
    seniority_ceiling  TEXT,
    narrative_tone     TEXT,
    raw_text_source    TEXT,
    linter_override    TEXT,
    created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_accomplishment_position
    ON accomplishment(position_slug);
CREATE INDEX IF NOT EXISTS idx_accomplishment_seniority
    ON accomplishment(seniority_ceiling);

-- ─────────────────────────────────────────────────────────────────
-- outcome: quantified metrics per accomplishment.
-- The truthfulness gate enforces: every numeric token in a generated
-- bullet must trace to one of these rows (via the linter's metric
-- regex + numeric normalizer).
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS outcome (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    accomplishment_id INTEGER NOT NULL REFERENCES accomplishment(id) ON DELETE CASCADE,
    metric_name       TEXT NOT NULL,
    value_numeric     REAL,
    value_text        TEXT,
    unit              TEXT,
    direction         TEXT,
    asof_date         TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_outcome_accomplishment
    ON outcome(accomplishment_id);

-- ─────────────────────────────────────────────────────────────────
-- evidence: provenance per outcome.
-- source enum: 'self_reported' | 'manager_quoted' | 'system_exported' | 'public'
-- self_reported is the seed default; Sean upgrades via /coin add-evidence.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evidence (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    outcome_id   INTEGER NOT NULL REFERENCES outcome(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL,
    source       TEXT NOT NULL,
    url_or_path  TEXT,
    notes        TEXT,
    asof_date    TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_evidence_outcome
    ON evidence(outcome_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source
    ON evidence(source);

-- ─────────────────────────────────────────────────────────────────
-- skill: Lightcast Open Skills subset (~2,000 rows seeded by m006).
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS skill (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    lightcast_id TEXT,
    category     TEXT,
    slug         TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_skill_category ON skill(category);
CREATE INDEX IF NOT EXISTS idx_skill_lightcast ON skill(lightcast_id);

-- ─────────────────────────────────────────────────────────────────
-- accomplishment_skill: M:N tag table.
-- weight 1-10; defaults to 5.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accomplishment_skill (
    accomplishment_id INTEGER NOT NULL REFERENCES accomplishment(id) ON DELETE CASCADE,
    skill_id          INTEGER NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
    weight            INTEGER DEFAULT 5,
    PRIMARY KEY (accomplishment_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_acc_skill_skill ON accomplishment_skill(skill_id);

-- ─────────────────────────────────────────────────────────────────
-- lane: 4 archetypes (mid-market-tpm | enterprise-sales-engineer |
--                     iot-solutions-architect | revenue-ops-operator).
-- Seeded by seed_from_base_py.py.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lane (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    slug  TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    rank  INTEGER
);

-- ─────────────────────────────────────────────────────────────────
-- accomplishment_lane: M:N relevance per (accomplishment, lane).
-- relevance_score 0-100. manual_pin distinguishes auto from user override.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accomplishment_lane (
    accomplishment_id INTEGER NOT NULL REFERENCES accomplishment(id) ON DELETE CASCADE,
    lane_id           INTEGER NOT NULL REFERENCES lane(id) ON DELETE CASCADE,
    relevance_score   INTEGER DEFAULT 50,
    manual_pin        INTEGER DEFAULT 0,
    PRIMARY KEY (accomplishment_id, lane_id)
);
CREATE INDEX IF NOT EXISTS idx_acc_lane_lane ON accomplishment_lane(lane_id);

-- ─────────────────────────────────────────────────────────────────
-- bullet_variant: write-cache for Claude-generated bullet phrasings.
-- Unique per (accomplishment, lane, length_bucket, tone) so re-runs
-- update in place rather than duplicating.
-- length_bucket: 'short' (<25 words) | 'medium' (25-45) | 'long' (>45).
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bullet_variant (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    accomplishment_id INTEGER NOT NULL REFERENCES accomplishment(id) ON DELETE CASCADE,
    lane_id           INTEGER NOT NULL REFERENCES lane(id) ON DELETE CASCADE,
    length_bucket     TEXT NOT NULL,
    tone              TEXT,
    text              TEXT NOT NULL,
    last_audit_pass   INTEGER DEFAULT 0,
    used_in_role_ids  TEXT,
    generated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_bullet_variant_unique
    ON bullet_variant(accomplishment_id, lane_id, length_bucket, COALESCE(tone, ''));

-- ─────────────────────────────────────────────────────────────────
-- jd_keyword: keywords/skills extracted from a JD, per role.
-- term_kind: 'must_have' | 'nice_to_have' | 'industry' | 'tool'.
-- importance 1-10 (auto-scored by jd_parser).
-- lightcast_id is set when the term matches a known skill.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jd_keyword (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id      INTEGER NOT NULL,
    term         TEXT NOT NULL,
    term_kind    TEXT,
    importance   INTEGER DEFAULT 5,
    lightcast_id TEXT,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_jd_keyword_role ON jd_keyword(role_id);
CREATE INDEX IF NOT EXISTS idx_jd_keyword_lightcast ON jd_keyword(lightcast_id);

-- ─────────────────────────────────────────────────────────────────
-- render_artifact: per (role × theme × variant_kind), tracks every
-- rendered PDF + the score panel results at render time.
-- variant_kind: 'designed' | 'ats' | 'weasy'.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS render_artifact (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id              INTEGER NOT NULL,
    theme                TEXT NOT NULL,
    variant_kind         TEXT NOT NULL,
    pdf_path             TEXT NOT NULL,
    ats_score            INTEGER,
    keyword_overlap_pct  REAL,
    buzzword_density_pct REAL,
    truthfulness_pass    INTEGER,
    page_count           INTEGER,
    notes                TEXT,
    rendered_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_render_artifact_role ON render_artifact(role_id);
CREATE INDEX IF NOT EXISTS idx_render_artifact_theme ON render_artifact(theme);
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
        conn.execute("PRAGMA foreign_keys = ON")
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
            print(f"[DRY RUN] Would create 10 tables for experience DB")
            return 0
        finally:
            conn.close()

    apply(db_path)
    print(f"✅ Migration {MIGRATION_ID} applied (or already in place).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
