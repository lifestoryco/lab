"""Tests for m005_posted_at — adds roles.posted_at column."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migrations import m005_posted_at


def _make_roles_table(db_path: str) -> None:
    """Create a minimal roles table mirroring pipeline.init_db's schema."""
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
        conn.commit()
    finally:
        conn.close()


def _columns(db_path: str, table: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [r[1] for r in rows]
    finally:
        conn.close()


def test_m005_adds_posted_at_column(tmp_path):
    db = tmp_path / "pipeline.db"
    _make_roles_table(str(db))
    m005_posted_at.apply(str(db))
    assert "posted_at" in _columns(str(db), "roles")


def test_m005_idempotent(tmp_path):
    db = tmp_path / "pipeline.db"
    _make_roles_table(str(db))
    m005_posted_at.apply(str(db))
    m005_posted_at.apply(str(db))  # second run must be a no-op
    cols = _columns(str(db), "roles")
    assert cols.count("posted_at") == 1


def test_m005_writes_schema_migrations_row(tmp_path):
    db = tmp_path / "pipeline.db"
    _make_roles_table(str(db))
    m005_posted_at.apply(str(db))
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute(
            "SELECT id FROM schema_migrations WHERE id = ?",
            ("m005_posted_at",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "m005_posted_at"
