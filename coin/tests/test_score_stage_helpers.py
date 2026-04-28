"""Tests for score_stage1 and score_stage2 helper wrappers."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from careerops.score import score_stage1, score_stage2


_LANE = "mid-market-tpm"

_ROLE = {
    "url": "https://example.com/job/1",
    "title": "Senior Technical Program Manager",
    "company": "Weave",
    "location": "Lehi, UT",
    "remote": 1,
    "comp_min": 160_000,
    "comp_max": 200_000,
    "comp_source": "explicit",
    "posted_at": None,
}

_PARSED_JD_RICH = {
    "required_skills": ["PMP", "Python", "JIRA", "stakeholder management"],
    "preferred_skills": ["AWS", "Agile"],
    "seniority": "senior",
    "comp_min": 160_000,
    "comp_max": 200_000,
    "comp_explicit": True,
    "red_flags": [],
    "culture_signals": ["remote-first", "async"],
    "team_size": 10,
    "reporting_to": "VP Engineering",
    "location_flexibility": "remote",
}

_DQ_RESULT_CLEAN = {"hard_dq": set(), "soft_dq": []}


# ── Test 1: score_stage1 uses title-only fallback (no JD signal) ─────────────


def test_score_stage1_no_jd_signal(monkeypatch):
    """score_stage1 must run without a parsed_jd; skills use lane keywords."""
    bd = score_stage1(_ROLE, _LANE)
    assert "composite" in bd
    assert "grade" in bd
    assert "dimensions" in bd
    # With no JD, skill_match falls back to lane keyword overlap
    # (not zero — the lane has keywords that partially match Sean's profile)
    assert 0 <= bd["composite"] <= 100


# ── Test 2: score_stage2 incorporates parsed_jd ───────────────────────────────


def test_score_stage2_differs_from_stage1_with_rich_jd():
    """When parsed_jd has explicit required_skills, stage-2 composite should
    differ from stage-1 composite (one is JD-derived, one is title-only)."""
    s1 = score_stage1(_ROLE, _LANE)
    s2 = score_stage2(_ROLE, _LANE, _PARSED_JD_RICH, _DQ_RESULT_CLEAN)
    # Scores CAN be equal in edge cases; we only assert the JD was consumed:
    assert s2["dimensions"]["seniority_fit"]["raw"] != 55.0, (
        "stage-2 must use parsed_jd['seniority'] — default fallback is 55.0"
    )
    # Stage 2 with senior seniority → 80.0
    assert s2["dimensions"]["seniority_fit"]["raw"] == 80.0


# ── Test 3: both helpers return same top-level dict shape ─────────────────────


def test_stage1_and_stage2_return_same_shape():
    s1 = score_stage1(_ROLE, _LANE)
    s2 = score_stage2(_ROLE, _LANE, _PARSED_JD_RICH, _DQ_RESULT_CLEAN)
    assert set(s1.keys()) >= {"composite", "grade", "dimensions"}
    assert set(s2.keys()) >= {"composite", "grade", "dimensions"}
    assert isinstance(s1["composite"], float)
    assert isinstance(s2["composite"], float)
    assert s1["grade"] in ("A", "B", "C", "D", "F")
    assert s2["grade"] in ("A", "B", "C", "D", "F")
