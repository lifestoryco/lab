"""Multi-variant render orchestrator + score panel persistence."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def seeded_db(tmp_path):
    """A DB with experience-tables seeded + a roles table for FK targets."""
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    conn = sqlite3.connect(str(db))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            company TEXT
        )
    """)
    conn.execute(
        "INSERT INTO roles (id, url, title, company) VALUES (4, 'https://x', 'TPM', 'Netflix')"
    )
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def coin_gen():
    """Truth-clean generated JSON: every metric has a matching outcome row."""
    from data.resumes.base import PROFILE
    gen = dict(PROFILE)
    gen.update({
        "archetype_id": "mid-market-tpm",
        "role_id": 4,
        "fit_score": 88,
        "executive_summary": "Senior TPM orchestrating wireless and IoT programs.",
        "top_bullets": [
            {"text": "Drove Cox program to $1M Y1 revenue 12 months ahead of schedule.", "accomplishment_id": 5},
            {"text": "Operationalized TitanX from concept to $27M Series A in under 2 years.", "accomplishment_id": 6},
        ],
    })
    return gen


def test_high_fit_emits_4_pdfs(seeded_db, coin_gen, tmp_path):
    from scripts.render_resume import render_multi_variant
    out = tmp_path / "out"
    artifacts = render_multi_variant(
        coin_gen, role_id=4, output_dir=out, high_fit=True, db_path=seeded_db,
    )
    # Expect: 1 weasy (skipped if render_pdf.render_pdf doesn't exist) + 3 designed + 1 ats.
    # Total >= 4 RenderCV outputs (3 designed + 1 ATS).
    rendercv_count = sum(1 for a in artifacts if a.get("variant_kind") in ("designed", "ats"))
    assert rendercv_count >= 4


def test_normal_fit_emits_2_pdfs(seeded_db, coin_gen, tmp_path):
    from scripts.render_resume import render_multi_variant
    out = tmp_path / "out"
    artifacts = render_multi_variant(
        coin_gen, role_id=4, output_dir=out, high_fit=False, db_path=seeded_db,
    )
    rendercv_count = sum(1 for a in artifacts if a.get("variant_kind") in ("designed", "ats"))
    # 1 designed + 1 ats.
    assert rendercv_count == 2


def test_score_panel_persists_render_artifact_rows(seeded_db, coin_gen, tmp_path):
    from scripts.render_resume import render_multi_variant
    from careerops import experience as exp
    out = tmp_path / "out"
    render_multi_variant(
        coin_gen, role_id=4, output_dir=out, high_fit=True, db_path=seeded_db,
    )
    rows = exp.list_render_artifacts(4, db_path=seeded_db)
    assert len(rows) >= 4
    # Every row should carry an ATS score and a truthfulness verdict.
    for r in rows:
        assert r["ats_score"] is not None
        assert r["truthfulness_pass"] is not None


def test_truth_gate_blocks_unbacked_metric(seeded_db, tmp_path):
    """A bullet that claims $5M when only $1M is in outcomes must fail truth gate."""
    from scripts.render_resume import render_multi_variant
    from data.resumes.base import PROFILE

    gen = dict(PROFILE)
    gen.update({
        "archetype_id": "mid-market-tpm",
        "role_id": 4,
        "fit_score": 60,
        "top_bullets": [
            # acc#5 has $1M in outcomes; bullet claims $5M → should fail.
            {"text": "Drove Cox program to $5M Y1 revenue.", "accomplishment_id": 5},
        ],
    })
    out = tmp_path / "out"
    artifacts = render_multi_variant(
        gen, role_id=4, output_dir=out, high_fit=False, db_path=seeded_db,
    )
    truth_passes = [a.get("truthfulness_pass") for a in artifacts if "truthfulness_pass" in a]
    # ALL variants should fail truth (same source bullets).
    assert all(t is False for t in truth_passes)
    assert any("TRUTH-GATE FAIL" in str(a.get("verdict", "")) for a in artifacts)


def test_explicit_variants_overrides_high_fit(seeded_db, coin_gen, tmp_path):
    from scripts.render_resume import render_multi_variant
    out = tmp_path / "out"
    artifacts = render_multi_variant(
        coin_gen, role_id=4, output_dir=out, high_fit=False,
        explicit_variants=4, db_path=seeded_db,
    )
    rendercv_count = sum(1 for a in artifacts if a.get("variant_kind") in ("designed", "ats"))
    assert rendercv_count >= 4


def test_score_panel_returns_verdict(seeded_db, coin_gen, tmp_path):
    from careerops.score_panel import score_artifact
    # First render one PDF.
    from scripts.render_rendercv import render_one
    out = tmp_path / "out"
    pdf = render_one(
        coin_gen, theme="engineeringresumes", variant="ats",
        output_dir=out, role_id=4,
    )
    scored = score_artifact(
        pdf_path=pdf, role_id=4, theme="engineeringresumes",
        variant_kind="ats", generated_json=coin_gen,
        db_path=seeded_db, persist=False,
    )
    assert scored["ats_score"] >= 70
    assert scored["truthfulness_pass"] is True
    assert scored["verdict"] in {"SHIP-READY", "USABLE"}
