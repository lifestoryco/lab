"""Tests for m009_notified_at — adds notified_at column for COIN-SCHEDULER."""
import os
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.migrations import m009_notified_at


def _make_roles_table(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE roles (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                url           TEXT UNIQUE NOT NULL,
                title         TEXT,
                company       TEXT,
                fit_score     REAL,
                status        TEXT DEFAULT 'discovered',
                discovered_at TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _columns(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA table_info(roles)").fetchall()
        return {r[1] for r in rows}
    finally:
        conn.close()


def test_m009_adds_notified_at_column(tmp_path):
    db_path = tmp_path / "test.db"
    _make_roles_table(db_path)
    m009_notified_at.apply(db_path)
    assert "notified_at" in _columns(db_path)


def test_m009_idempotent(tmp_path):
    db_path = tmp_path / "test.db"
    _make_roles_table(db_path)
    m009_notified_at.apply(db_path)
    cols_after_first = _columns(db_path)
    m009_notified_at.apply(db_path)  # should not error
    assert _columns(db_path) == cols_after_first


def test_m009_records_schema_migrations_row(tmp_path):
    db_path = tmp_path / "test.db"
    _make_roles_table(db_path)
    m009_notified_at.apply(db_path)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT id FROM schema_migrations WHERE id = 'm009_notified_at'"
        ).fetchall()
        assert len(rows) == 1
    finally:
        conn.close()
