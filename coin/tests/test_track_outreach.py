"""Tests for scripts/track_outreach.py."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.migrations import m003_connections_outreach as m003
from scripts import track_outreach as ot


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Create an isolated DB with the connections+outreach schema applied,
    monkeypatch the module to use it."""
    db_path = tmp_path / "test.db"
    m003.apply(db_path)

    # Seed a connection and an outreach row
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "INSERT INTO connections (full_name, linkedin_url, company, position) "
        "VALUES (?, ?, ?, ?)",
        ("Jane Doe", "https://linkedin.com/in/jane", "Cox", "VP Eng"),
    )
    conn.execute(
        "INSERT INTO outreach (role_id, connection_id, warmth_score, draft_message) "
        "VALUES (?, ?, ?, ?)",
        (1, 1, 90.0, "Hey Jane — long time."),
    )
    conn.commit()
    conn.close()

    # Patch the module's _conn to hit our temp db
    def _temp_conn():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(ot, "_conn", _temp_conn)
    return db_path


def test_update_sets_sent_at(temp_db):
    row = ot.update(1, "sent")
    assert row["sent_at"] is not None
    assert row["replied_at"] is None


def test_update_sets_replied_at(temp_db):
    row = ot.update(1, "replied")
    assert row["replied_at"] is not None


def test_update_with_note(temp_db):
    row = ot.update(1, "sent", note="DM sent at 9am Tue")
    assert row["notes"] == "DM sent at 9am Tue"


def test_update_invalid_action_raises(temp_db):
    with pytest.raises(ValueError, match="action must be one of"):
        ot.update(1, "ghosted")


def test_update_unknown_id_raises(temp_db):
    with pytest.raises(ValueError, match="not found"):
        ot.update(999, "sent")


def test_list_open_only_returns_unsent(temp_db):
    open_before = ot.list_open()
    assert len(open_before) == 1
    assert open_before[0]["sent_at"] is None
    assert open_before[0]["contact_name"] == "Jane Doe"

    ot.update(1, "sent")
    open_after = ot.list_open()
    assert open_after == []


def test_list_open_filters_by_role(temp_db):
    rows = ot.list_open(role_id=1)
    assert len(rows) == 1
    rows_other = ot.list_open(role_id=999)
    assert rows_other == []


def test_missing_outreach_table_raises(tmp_path, monkeypatch):
    """update() must give a clear error if migration m003 hasn't run."""
    db_path = tmp_path / "no_schema.db"
    sqlite3.connect(str(db_path)).close()  # empty DB

    def _temp_conn():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(ot, "_conn", _temp_conn)
    with pytest.raises(RuntimeError, match="m003_connections_outreach"):
        ot.update(1, "sent")
