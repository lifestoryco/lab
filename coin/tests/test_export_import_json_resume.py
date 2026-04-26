"""JSON Resume v1.0.0 export / import round-trip."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def seeded_db(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    return db


def test_export_contains_required_sections(seeded_db):
    from scripts.export_json_resume import build_json_resume
    payload = build_json_resume(db_path=seeded_db)
    for key in ("$schema", "basics", "work", "education", "skills", "certificates", "meta"):
        assert key in payload


def test_export_basics_has_name_email(seeded_db):
    from scripts.export_json_resume import build_json_resume
    payload = build_json_resume(db_path=seeded_db)
    assert payload["basics"]["name"] == "Sean Ivins"
    assert "@" in payload["basics"]["email"]


def test_export_work_includes_all_positions(seeded_db):
    from scripts.export_json_resume import build_json_resume
    payload = build_json_resume(db_path=seeded_db)
    company_names = [w["name"] for w in payload["work"]]
    assert "CA Engineering" in company_names
    assert "Hydrant (Software Engineering Firm)" in company_names
    assert "Utah Broadband" in company_names


def test_export_highlights_grouped_by_position(seeded_db):
    from scripts.export_json_resume import build_json_resume
    payload = build_json_resume(db_path=seeded_db)
    cox_position = next(w for w in payload["work"] if "Hydrant" in w["name"])
    # Hydrant has 3 bullets in base.py.
    assert len(cox_position["highlights"]) >= 2


def test_round_trip_preserves_position_count(seeded_db, tmp_path):
    """Export → import into fresh DB → same position count."""
    from scripts.export_json_resume import build_json_resume
    from scripts.import_json_resume import import_json_resume
    from scripts.migrations import m005_experience_db, m006_seed_lightcast

    payload = build_json_resume(db_path=seeded_db)

    db2 = tmp_path / "fresh.db"
    m005_experience_db.apply(db2)
    m006_seed_lightcast.apply(db2)
    stats = import_json_resume(payload, apply=True, db_path=db2)
    assert stats["positions_seen"] == 4
    assert stats["accomplishments_added"] >= 8


def test_dry_run_does_not_write(seeded_db, tmp_path):
    from scripts.import_json_resume import import_json_resume
    from scripts.migrations import m005_experience_db

    db2 = tmp_path / "dry.db"
    m005_experience_db.apply(db2)
    payload = {
        "work": [{"name": "TestCo", "highlights": ["foo bar baz"]}],
        "skills": [],
    }
    stats = import_json_resume(payload, apply=False, db_path=db2)
    # Dry run COUNTS but doesn't write.
    assert stats["accomplishments_added"] == 1
    conn = sqlite3.connect(str(db2))
    n = conn.execute("SELECT COUNT(*) FROM accomplishment").fetchone()[0]
    conn.close()
    assert n == 0
