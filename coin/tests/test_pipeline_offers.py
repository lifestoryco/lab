"""Tests for careerops.pipeline.insert_offer + list_offers integration with
migration m002."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops import pipeline as p
from scripts.migrations import m002_offers_table as m002


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Run insert_offer / list_offers against an isolated DB.

    pipeline._conn() reads DB_PATH from module globals; patching the
    module-level constant is enough as long as tests don't call init_db
    (which would reach into config to recreate paths)."""
    db_path = tmp_path / "pipeline.db"
    m002.apply(db_path)
    monkeypatch.setattr(p, "DB_PATH", str(db_path))
    return db_path


def test_insert_offer_writes_row(temp_db):
    oid = p.insert_offer({
        "company": "Filevine",
        "title": "Senior Solutions Engineer",
        "base_salary": 185_000,
    })
    assert oid >= 1
    rows = p.list_offers(status="active")
    assert len(rows) == 1
    assert rows[0]["company"] == "Filevine"
    assert rows[0]["base_salary"] == 185_000
    # received_at defaulted to today
    assert rows[0]["received_at"]


def test_insert_offer_missing_required_raises(temp_db):
    """Regression: previously would silently INSERT NULL and surface a low-context
    sqlite IntegrityError. Now raises ValueError naming the missing keys."""
    with pytest.raises(ValueError, match="missing required keys"):
        p.insert_offer({"company": "X"})  # missing title + base_salary
    with pytest.raises(ValueError, match="missing required keys"):
        p.insert_offer({})


def test_list_offers_default_active(temp_db):
    p.insert_offer({"company": "A", "title": "TPM", "base_salary": 200_000})
    p.insert_offer({
        "company": "B", "title": "TPM", "base_salary": 180_000, "status": "declined",
    })
    active = p.list_offers()  # default
    assert len(active) == 1
    assert active[0]["company"] == "A"

    declined = p.list_offers(status="declined")
    assert len(declined) == 1
    assert declined[0]["company"] == "B"

    all_rows = p.list_offers(status=None)
    assert len(all_rows) == 2
