"""Migration m003 (connections + outreach) — schema + idempotency."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.migrations import m003_connections_outreach as m003


def test_apply_creates_both_tables(tmp_path):
    db = tmp_path / "test.db"
    m003.apply(db)

    conn = sqlite3.connect(str(db))
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for required in ("connections", "outreach", "schema_migrations"):
            assert required in tables
    finally:
        conn.close()


def test_apply_is_idempotent(tmp_path):
    db = tmp_path / "test.db"
    m003.apply(db)
    m003.apply(db)  # second run

    conn = sqlite3.connect(str(db))
    try:
        applied = conn.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE id = ?",
            ("003_connections_outreach",),
        ).fetchone()[0]
        assert applied == 1
    finally:
        conn.close()


def test_apply_creates_indexes(tmp_path):
    db = tmp_path / "test.db"
    m003.apply(db)

    conn = sqlite3.connect(str(db))
    try:
        idx = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()
        }
        for required in (
            "idx_connections_company",
            "idx_connections_seniority",
            "idx_outreach_role",
            "idx_outreach_connection",
        ):
            assert required in idx
    finally:
        conn.close()
