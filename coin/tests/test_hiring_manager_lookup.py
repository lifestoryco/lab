"""Tests for the cover-letter recipient_name auto-population path:

- migration m004 adds outreach.contact_role + outreach.target_role_id
- careerops.pipeline.tag_outreach_role validates contact_role enum
- careerops.pipeline.find_hiring_manager_for_role joins outreach × connections
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops import pipeline as p
from scripts.migrations import (
    m003_connections_outreach as m003,
    m004_outreach_role_tag as m004,
)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "pipeline.db"
    m003.apply(db_path)
    m004.apply(db_path)
    monkeypatch.setattr(p, "DB_PATH", str(db_path))

    # Seed connections + outreach
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO connections (id, full_name, linkedin_url, company, position) "
        "VALUES (1, 'Jane Doe', 'https://linkedin.com/in/jane', 'Filevine', 'VP Eng')"
    )
    conn.execute(
        "INSERT INTO connections (id, full_name, linkedin_url, company, position) "
        "VALUES (2, 'Bob Recruiter', 'https://linkedin.com/in/bob', 'Filevine', 'TA Lead')"
    )
    conn.execute(
        "INSERT INTO outreach (id, role_id, connection_id, warmth_score, draft_message) "
        "VALUES (10, 137, 1, 92.0, 'Hey Jane —')"
    )
    conn.execute(
        "INSERT INTO outreach (id, role_id, connection_id, warmth_score, draft_message) "
        "VALUES (11, 137, 2, 78.0, 'Hi Bob —')"
    )
    conn.commit()
    conn.close()
    return db_path


def test_m004_adds_columns(tmp_path):
    db = tmp_path / "test.db"
    m003.apply(db)
    m004.apply(db)
    conn = sqlite3.connect(str(db))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(outreach)").fetchall()}
    conn.close()
    assert "contact_role" in cols
    assert "target_role_id" in cols


def test_m004_idempotent(tmp_path):
    db = tmp_path / "test.db"
    m003.apply(db)
    m004.apply(db)
    m004.apply(db)
    conn = sqlite3.connect(str(db))
    n = conn.execute(
        "SELECT COUNT(*) FROM schema_migrations WHERE id = ?",
        ("004_outreach_role_tag",),
    ).fetchone()[0]
    conn.close()
    assert n == 1


def test_m004_runs_m003_inline_on_fresh_db(tmp_path):
    """m004 must self-bootstrap when m003 hasn't run yet (e.g. brand-new DB)."""
    db = tmp_path / "fresh.db"
    m004.apply(db)
    conn = sqlite3.connect(str(db))
    tables = {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()
    assert "connections" in tables
    assert "outreach" in tables


def test_tag_outreach_role_sets_hiring_manager(temp_db):
    p.tag_outreach_role(10, "hiring_manager", target_role_id=137)
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute(
        "SELECT contact_role, target_role_id FROM outreach WHERE id = ?", (10,)
    ).fetchone()
    conn.close()
    assert row[0] == "hiring_manager"
    assert row[1] == 137


def test_tag_outreach_role_rejects_invalid_role(temp_db):
    with pytest.raises(ValueError, match="contact_role must be one of"):
        p.tag_outreach_role(10, "best_friend")
    with pytest.raises(ValueError, match="contact_role must be one of"):
        p.tag_outreach_role(10, "")


def test_find_hiring_manager_returns_tagged_contact(temp_db):
    p.tag_outreach_role(10, "hiring_manager", target_role_id=137)
    hm = p.find_hiring_manager_for_role(137)
    assert hm is not None
    assert hm["full_name"] == "Jane Doe"
    assert hm["contact_role_tag"] == "hiring_manager"


def test_find_hiring_manager_returns_none_when_no_tag(temp_db):
    """Untagged outreach rows must not be surfaced as hiring manager."""
    hm = p.find_hiring_manager_for_role(137)
    assert hm is None


def test_find_hiring_manager_ignores_other_role_tags(temp_db):
    """A 'recruiter' tag on the same role must NOT be returned as hiring manager."""
    p.tag_outreach_role(11, "recruiter", target_role_id=137)
    hm = p.find_hiring_manager_for_role(137)
    assert hm is None


def test_find_hiring_manager_picks_most_recent_when_multiple(temp_db):
    """Sean might tag two contacts as hiring_manager (rare but possible —
    e.g. internal restructure mid-process). The helper returns the most
    recently drafted outreach's connection."""
    # Tag both — second tag (id 11) drafts second by default insert order
    p.tag_outreach_role(10, "hiring_manager", target_role_id=137)
    p.tag_outreach_role(11, "hiring_manager", target_role_id=137)
    # Bump 11's drafted_at to be later than 10's
    conn = sqlite3.connect(str(temp_db))
    conn.execute(
        "UPDATE outreach SET drafted_at = datetime('now', '+1 hour') WHERE id = 11"
    )
    conn.commit()
    conn.close()
    hm = p.find_hiring_manager_for_role(137)
    assert hm["full_name"] == "Bob Recruiter"


def test_find_hiring_manager_handles_missing_schema(tmp_path, monkeypatch):
    """If the DB has no connections/outreach tables (fresh init), the helper
    returns None instead of raising."""
    db = tmp_path / "empty.db"
    sqlite3.connect(str(db)).close()
    monkeypatch.setattr(p, "DB_PATH", str(db))
    assert p.find_hiring_manager_for_role(1) is None


def test_find_hiring_manager_via_target_role_id(temp_db):
    """The helper checks both role_id AND target_role_id columns — Sean
    might tag a contact as hiring_manager for a DIFFERENT role than the
    outreach was originally drafted for (e.g. same person moves to lead a
    new req)."""
    # Outreach 10 was drafted for role_id=137. Tag it as hiring_manager for
    # a different target_role_id=200.
    p.tag_outreach_role(10, "hiring_manager", target_role_id=200)
    hm = p.find_hiring_manager_for_role(200)
    assert hm is not None
    assert hm["full_name"] == "Jane Doe"
