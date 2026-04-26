"""Score panel — truth gate + keyword overlap + verdict logic."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops.score_panel import (
    truthfulness_gate,
    keyword_overlap_pct,
    bullet_density_per_role,
    _collect_bullets,
    ScorePanel,
)


@pytest.fixture
def seeded_db(tmp_path):
    from scripts.seed_from_base_py import seed
    db = tmp_path / "t.db"
    seed(db)
    conn = sqlite3.connect(str(db))
    conn.execute(
        "CREATE TABLE roles (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE)"
    )
    conn.execute("INSERT INTO roles (id, url) VALUES (4, 'https://x')")
    conn.commit()
    conn.close()
    return db


def test_collect_bullets_handles_string_and_dict_forms():
    gen = {
        "top_bullets": [
            "string form",
            {"text": "dict form", "accomplishment_id": 5},
        ],
        "positions": [
            {"bullets": ["pos string", {"text": "pos dict", "accomplishment_id": 1}]},
        ],
    }
    bullets = _collect_bullets(gen)
    assert ("string form", None) in bullets
    assert ("dict form", 5) in bullets
    assert ("pos string", None) in bullets
    assert ("pos dict", 1) in bullets


def test_truth_gate_passes_with_clean_bullets(seeded_db):
    gen = {
        "top_bullets": [
            {"text": "Drove Cox to $1M Y1 revenue 12 months ahead of schedule.", "accomplishment_id": 5},
            {"text": "Operationalized TitanX from concept to $27M Series A in under 2 years.", "accomplishment_id": 6},
        ]
    }
    passed, fails, n_v, n_t = truthfulness_gate(gen, db_path=seeded_db)
    assert passed
    assert not fails
    assert n_v >= 4


def test_truth_gate_fails_on_unbacked_metric(seeded_db):
    gen = {
        "top_bullets": [
            {"text": "Drove Cox to $5M Y1 revenue.", "accomplishment_id": 5},
        ]
    }
    passed, fails, _, _ = truthfulness_gate(gen, db_path=seeded_db)
    assert not passed
    assert any("$5M" in f for f in fails)


def test_truth_gate_fails_on_kill_word(seeded_db):
    gen = {
        "top_bullets": [
            {"text": "Was responsible for the Cox program.", "accomplishment_id": 5},
        ]
    }
    passed, fails, _, _ = truthfulness_gate(gen, db_path=seeded_db)
    assert not passed
    assert any("kill-words" in f for f in fails)


def test_truth_gate_skips_unattached_bullets_for_metric_check(seeded_db):
    """Unattached bullets (top_bullets without accomplishment_id) get
    buzzword/kill-word checks but not metric verification."""
    gen = {
        "top_bullets": [
            "Drove Cox to $99M Y1 revenue.",  # no accomplishment_id
        ]
    }
    passed, fails, _, _ = truthfulness_gate(gen, db_path=seeded_db)
    # Should pass — no metric check applied to unattached bullet.
    assert passed


def test_keyword_overlap_returns_none_when_no_keywords(seeded_db):
    gen = {"top_bullets": []}
    pct = keyword_overlap_pct(gen, role_id=4, db_path=seeded_db)
    assert pct is None  # no jd_keyword rows for role 4


def test_keyword_overlap_calculates_pct(seeded_db):
    """Insert some must_have keywords + verify overlap math."""
    from careerops import experience as exp
    exp.upsert_jd_keyword(role_id=4, term="Program Management",
                          term_kind="must_have", db_path=seeded_db)
    exp.upsert_jd_keyword(role_id=4, term="Wireless",
                          term_kind="must_have", db_path=seeded_db)
    exp.upsert_jd_keyword(role_id=4, term="Quantum Computing",  # not in resume
                          term_kind="must_have", db_path=seeded_db)
    gen = {
        "name": "Sean Ivins",
        "default_summary": "Senior TPM with program management and wireless experience.",
        "top_bullets": [],
        "positions": [],
        "skills": [],
        "skills_grid": {},
    }
    pct = keyword_overlap_pct(gen, role_id=4, db_path=seeded_db)
    # 2 of 3 keywords match → ~66.7%
    assert pct is not None
    assert 60 < pct < 70


def test_bullet_density_per_role():
    gen = {
        "positions": [
            {"bullets": ["a", "b", "c"]},
            {"bullets": ["x", "y"]},
        ]
    }
    assert bullet_density_per_role(gen) == [3, 2]


def test_score_panel_verdict_ship_ready():
    p = ScorePanel(
        role_id=1, theme="t", variant_kind="designed", pdf_path="/tmp/p",
        ats_score=92, keyword_overlap_pct=72.0, buzzword_density_pct=2.1,
        truthfulness_pass=True, page_count=1,
    )
    assert p.verdict() == "SHIP-READY"


def test_score_panel_verdict_truth_gate_fail():
    p = ScorePanel(
        role_id=1, theme="t", variant_kind="designed", pdf_path="/tmp/p",
        ats_score=92, keyword_overlap_pct=72.0, buzzword_density_pct=2.1,
        truthfulness_pass=False, page_count=1,
    )
    assert p.verdict() == "TRUTH-GATE FAIL"


def test_score_panel_verdict_stuffing():
    p = ScorePanel(
        role_id=1, theme="t", variant_kind="designed", pdf_path="/tmp/p",
        ats_score=92, keyword_overlap_pct=72.0, buzzword_density_pct=8.0,
        truthfulness_pass=True, page_count=1,
    )
    assert p.verdict() == "STUFFING"


def test_score_panel_verdict_too_long():
    p = ScorePanel(
        role_id=1, theme="t", variant_kind="designed", pdf_path="/tmp/p",
        ats_score=92, keyword_overlap_pct=72.0, buzzword_density_pct=2.0,
        truthfulness_pass=True, page_count=3,
    )
    assert p.verdict() == "TOO-LONG"
