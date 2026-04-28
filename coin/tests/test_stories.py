"""Tests for careerops.stories — STAR proof-point library."""
import datetime as _dt
import os
from pathlib import Path

import pytest
import yaml

from careerops import stories as stories_mod


@pytest.fixture
def tmp_stories_path(tmp_path, monkeypatch):
    p = tmp_path / "stories.yml"
    monkeypatch.setattr(stories_mod, "STORIES_PATH", p)
    return p


def _valid_story(**overrides):
    base = {
        "id": "test-story",
        "role": "hydrant",
        "project": "Test project",
        "dates": {"start": "2020-01", "end": "2021-06"},
        "lanes_relevant_for": ["mid-market-tpm"],
        "situation": "Test situation",
        "task": "Test task",
        "action": "Test action",
        "result": "Test result",
        "metrics": [
            {"value": "1M", "unit": "USD", "description": "revenue"}
        ],
        "team": {"size": 5, "composition": "5 engineers", "sean_role": "PM"},
        "named_account_ok": True,
        "related_skills": ["program management", "B2B SaaS"],
        "grade": "A",
        "created": "2026-04-27",
        "last_validated": "2026-04-27",
    }
    base.update(overrides)
    return base


# ── load / get ──────────────────────────────────────────────────────────────

def test_load_stories_empty_file_returns_empty_list(tmp_stories_path):
    assert stories_mod.load_stories() == []


def test_load_stories_populated(tmp_stories_path):
    tmp_stories_path.write_text(yaml.safe_dump({"version": 1, "stories": [_valid_story()]}))
    out = stories_mod.load_stories()
    assert len(out) == 1
    assert out[0]["id"] == "test-story"


def test_load_stories_malformed_yaml_raises(tmp_stories_path):
    tmp_stories_path.write_text("version: 1\nstories: [unterminated\n")
    with pytest.raises(ValueError, match="malformed YAML"):
        stories_mod.load_stories()


# ── add / update ────────────────────────────────────────────────────────────

def test_add_story_writes_correctly(tmp_stories_path):
    sid = stories_mod.add_story(_valid_story())
    assert sid == "test-story"
    assert tmp_stories_path.exists()
    on_disk = yaml.safe_load(tmp_stories_path.read_text())
    assert on_disk["stories"][0]["id"] == "test-story"


def test_add_story_atomic_no_temp_remains(tmp_stories_path):
    stories_mod.add_story(_valid_story())
    leftover = list(tmp_stories_path.parent.glob(".stories.*.yml.tmp"))
    assert leftover == []


def test_add_story_rejects_duplicate_id(tmp_stories_path):
    stories_mod.add_story(_valid_story(id="dup"))
    with pytest.raises(ValueError, match="duplicate story id"):
        stories_mod.add_story(_valid_story(id="dup"))


def test_update_story_merges_partial(tmp_stories_path):
    stories_mod.add_story(_valid_story(id="s1", grade="A"))
    ok = stories_mod.update_story("s1", {"grade": "B"})
    assert ok is True
    assert stories_mod.get_story_by_id("s1")["grade"] == "B"


def test_update_story_does_not_clobber(tmp_stories_path):
    stories_mod.add_story(_valid_story(id="s1"))
    stories_mod.update_story("s1", {"grade": "B"})
    s = stories_mod.get_story_by_id("s1")
    assert s["situation"] == "Test situation"
    assert s["metrics"][0]["value"] == "1M"


def test_update_story_returns_false_on_missing(tmp_stories_path):
    stories_mod.add_story(_valid_story(id="s1"))
    assert stories_mod.update_story("nope", {"grade": "B"}) is False


# ── validate ────────────────────────────────────────────────────────────────

def test_validate_story_accepts_valid():
    valid, errors = stories_mod.validate_story(_valid_story())
    assert valid is True
    assert errors == []


def test_validate_story_rejects_missing_field():
    s = _valid_story()
    del s["situation"]
    valid, errors = stories_mod.validate_story(s)
    assert valid is False
    assert any("situation" in e for e in errors)


def test_validate_story_rejects_malformed_dates():
    bad_inputs = [
        _valid_story(dates={"start": "2026-13", "end": "2026-06"}),
        _valid_story(dates={"start": "April 2026", "end": "present"}),
        _valid_story(dates={"start": "2026/04", "end": "present"}),
    ]
    for s in bad_inputs:
        valid, errors = stories_mod.validate_story(s)
        assert valid is False, f"should reject {s['dates']}"
        assert any("dates.start" in e or "dates.end" in e for e in errors)


def test_validate_story_rejects_invalid_lane():
    s = _valid_story(lanes_relevant_for=["mid-market-tpm", "data-engineer"])
    valid, errors = stories_mod.validate_story(s)
    assert valid is False
    assert any("invalid lane" in e for e in errors)


def test_validate_story_rejects_bad_grade():
    s = _valid_story(grade="X")
    valid, errors = stories_mod.validate_story(s)
    assert valid is False
    assert any("grade" in e for e in errors)


# ── query ───────────────────────────────────────────────────────────────────

def test_find_stories_for_lane_filters_and_min_grade(tmp_stories_path):
    stories_mod.add_story(_valid_story(id="a", grade="A", lanes_relevant_for=["mid-market-tpm"]))
    stories_mod.add_story(_valid_story(id="b", grade="C", lanes_relevant_for=["mid-market-tpm"]))
    stories_mod.add_story(_valid_story(id="c", grade="A", lanes_relevant_for=["enterprise-sales-engineer"]))

    out = stories_mod.find_stories_for_lane("mid-market-tpm", min_grade="B")
    ids = [s["id"] for s in out]
    assert "a" in ids
    assert "b" not in ids  # filtered by min_grade
    assert "c" not in ids  # filtered by lane


def test_find_stories_for_skills_ranks_by_overlap_grade_recency(tmp_stories_path, monkeypatch):
    # Freeze "today" for deterministic recency via the module-level helper
    monkeypatch.setattr(stories_mod, "_today", lambda: _dt.date(2026, 4, 27))

    stories_mod.add_story(_valid_story(
        id="hi-overlap-A-recent", grade="A",
        last_validated="2026-04-01",
        related_skills=["ruby", "rails", "postgres"],
    ))
    stories_mod.add_story(_valid_story(
        id="hi-overlap-A-stale", grade="A",
        last_validated="2020-01-01",
        related_skills=["ruby", "rails", "postgres"],
    ))
    stories_mod.add_story(_valid_story(
        id="lo-overlap-A-recent", grade="A",
        last_validated="2026-04-01",
        related_skills=["ruby"],
    ))
    stories_mod.add_story(_valid_story(
        id="hi-overlap-C-recent", grade="C",
        last_validated="2026-04-01",
        related_skills=["ruby", "rails", "postgres"],
    ))

    ranked = stories_mod.find_stories_for_skills(["ruby", "rails", "postgres"])
    ids = [s["id"] for s in ranked]
    assert ids[0] == "hi-overlap-A-recent"  # 3 * 3 * 1.0 = 9
    # hi-overlap-A-stale: 3*3*0.5=4.5; hi-overlap-C-recent: 3*1*1=3; lo-overlap-A-recent: 1*3*1=3
    assert ids[1] == "hi-overlap-A-stale"


def test_get_story_by_id_hit_and_miss(tmp_stories_path):
    stories_mod.add_story(_valid_story(id="abc"))
    assert stories_mod.get_story_by_id("abc")["id"] == "abc"
    assert stories_mod.get_story_by_id("nope") is None


def test_seeded_stories_yml_is_valid():
    """The 5 seeded stories from base.py PROFILE must validate cleanly."""
    repo_seed = Path(__file__).resolve().parent.parent / "data" / "resumes" / "stories.yml"
    if not repo_seed.exists():
        pytest.skip("seeded stories.yml not present in this checkout")
    data = yaml.safe_load(repo_seed.read_text())
    assert data["version"] == 1
    seeded = data["stories"]
    assert len(seeded) >= 5
    expected_ids = {
        "cox-true-local-labs",
        "titanx-fractional-coo",
        "utah-broadband-acquisition",
        "arr-growth-6m-to-13m",
        "global-engineering-orchestration",
    }
    actual_ids = {s["id"] for s in seeded}
    assert expected_ids.issubset(actual_ids)
    for s in seeded:
        valid, errors = stories_mod.validate_story(s)
        assert valid, f"seeded story {s['id']} failed validation: {errors}"
