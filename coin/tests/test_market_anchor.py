"""Tests for careerops.pipeline.insert_market_anchor + list_market_anchors."""

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
    db_path = tmp_path / "pipeline.db"
    m002.apply(db_path)
    monkeypatch.setattr(p, "DB_PATH", str(db_path))
    return db_path


def test_insert_market_anchor_writes_row(temp_db):
    oid = p.insert_market_anchor(
        company="Filevine",
        title="Senior SE (L5)",
        base_salary=185_000,
        rsu_total_value=120_000,
        annual_bonus_target_pct=0.10,
        source="Levels.fyi",
        notes="P50 from levels.fyi/companies/filevine retrieved 2026-04-25",
    )
    assert oid >= 1
    anchors = p.list_market_anchors()
    assert len(anchors) == 1
    row = anchors[0]
    assert row["company"] == "Filevine"
    assert row["base_salary"] == 185_000
    assert row["status"] == "market_anchor"
    assert "Levels.fyi" in row["notes"]
    assert "P50" in row["notes"]


def test_market_anchor_excluded_from_active_list(temp_db):
    """ofertas Step 3 calls list_offers() which defaults to status='active';
    the anchor must NOT appear there or it'd contaminate Y1-best ranking."""
    p.insert_offer({"company": "Real", "title": "TPM", "base_salary": 200_000})
    p.insert_market_anchor(
        company="Real", title="TPM (L5)", base_salary=210_000, source="Levels.fyi"
    )
    active = p.list_offers()  # default 'active'
    anchors = p.list_market_anchors()
    assert len(active) == 1
    assert active[0]["company"] == "Real" and active[0]["status"] == "active"
    assert len(anchors) == 1
    assert anchors[0]["company"] == "Real" and anchors[0]["status"] == "market_anchor"


def test_market_anchor_required_fields(temp_db):
    with pytest.raises(ValueError, match="requires"):
        p.insert_market_anchor(company="", title="X", base_salary=100_000)
    with pytest.raises(ValueError, match="requires"):
        p.insert_market_anchor(company="X", title="", base_salary=100_000)
    with pytest.raises(ValueError, match="requires"):
        p.insert_market_anchor(company="X", title="Y", base_salary=0)


def test_market_anchor_combined_for_comparison(temp_db):
    """ofertas mode docs combine list_offers(active) + list_market_anchors()
    so the anchor sits alongside the real offer for the comparison table."""
    p.insert_offer({"company": "A", "title": "TPM", "base_salary": 180_000})
    p.insert_market_anchor(
        company="A_market", title="TPM (L5)", base_salary=200_000, source="Levels.fyi"
    )
    combined = p.list_offers(status="active") + p.list_market_anchors()
    assert len(combined) == 2
    statuses = {row["status"] for row in combined}
    assert statuses == {"active", "market_anchor"}
