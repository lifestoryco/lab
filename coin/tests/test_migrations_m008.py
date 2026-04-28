"""Tests for m008_two_stage_score — adds two-stage scoring columns."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migrations import m008_two_stage_score


def _make_roles_table(db_path: str, with_fit_score: bool = False) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE roles (
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
                updated_at    TEXT
            )
        """)
        if with_fit_score:
            conn.execute(
                "INSERT INTO roles (url, title, fit_score, status, discovered_at) "
                "VALUES (?, ?, ?, ?, datetime('now'))",
                ("https://example.com/1", "Senior TPM", 78.5, "scored"),
            )
        conn.commit()
    finally:
        conn.close()


def _columns(db_path: str, table: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    finally:
        conn.close()


# ── Test 1: columns exist after migration ────────────────────────────────────


def test_m008_adds_stage_columns(tmp_path):
    db = str(tmp_path / "pipeline.db")
    _make_roles_table(db)
    m008_two_stage_score.apply(db)
    cols = _columns(db, "roles")
    for col in ("score_stage1", "score_stage2", "score_stage", "jd_parsed_at"):
        assert col in cols, f"column {col!r} missing after migration"


# ── Test 2: idempotency ───────────────────────────────────────────────────────


def test_m008_idempotent(tmp_path):
    db = str(tmp_path / "pipeline.db")
    _make_roles_table(db)
    m008_two_stage_score.apply(db)
    m008_two_stage_score.apply(db)  # second run must be a no-op
    cols = _columns(db, "roles")
    for col in ("score_stage1", "score_stage2", "score_stage", "jd_parsed_at"):
        assert cols.count(col) == 1, f"column {col!r} appears more than once after double apply"


# ── Test 3: backfill copies fit_score → score_stage1 ─────────────────────────


def test_m008_backfills_score_stage1_from_fit_score(tmp_path):
    db = str(tmp_path / "pipeline.db")
    _make_roles_table(db, with_fit_score=True)
    m008_two_stage_score.apply(db)
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("SELECT fit_score, score_stage1 FROM roles LIMIT 1").fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == row[1] == 78.5, "score_stage1 must equal fit_score after backfill"


# ── Test 4: schema_migrations row written ────────────────────────────────────


def test_m008_writes_schema_migrations_row(tmp_path):
    db = str(tmp_path / "pipeline.db")
    _make_roles_table(db)
    m008_two_stage_score.apply(db)
    conn = sqlite3.connect(db)
    try:
        row = conn.execute(
            "SELECT id FROM schema_migrations WHERE id = ?",
            ("m008_two_stage_score",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "m008_two_stage_score"
