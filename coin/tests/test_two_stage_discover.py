"""Tests for COIN-SCORE-V2 two-stage scoring pipeline helpers."""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import careerops.pipeline as pip_mod


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(pip_mod, "DB_PATH", str(tmp_path / "pipeline.db"))
    pip_mod.init_db()
    return tmp_path


def _insert_role(url: str = "https://example.com/job/1") -> dict:
    return {
        "url": url,
        "title": "Senior TPM",
        "company": "Acme",
        "location": "Salt Lake City, UT",
        "lane": "mid-market-tpm",
        "comp_min": 160_000,
        "comp_source": "explicit",
    }


# ── Test 1: update_score_stage1 persists to score_stage1 ─────────────────────


def test_update_score_stage1_persists_column(db):
    rid = pip_mod.upsert_role(_insert_role())
    pip_mod.update_score_stage1(rid, 78.5)

    role = pip_mod.get_role(rid)
    assert role["score_stage1"] == 78.5


# ── Test 2: update_score_stage2 persists score + jd_parsed_at ────────────────


def test_update_score_stage2_persists_score_and_timestamp(db):
    rid = pip_mod.upsert_role(_insert_role())
    pip_mod.update_score_stage1(rid, 70.0)

    parsed = {"required_skills": ["Python"], "comp_explicit": False}
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pip_mod.update_score_stage2(rid, 83.2, parsed, ts)

    role = pip_mod.get_role(rid)
    assert role["score_stage2"] == 83.2
    assert role["jd_parsed_at"] is not None
    # jd_parsed should also contain the parsed dict
    stored = json.loads(role["jd_parsed"])
    assert stored["required_skills"] == ["Python"]


# ── Test 3: get_top_n_for_deep_score ordering and filters ────────────────────


def test_get_top_n_for_deep_score_ordering_and_filter(db):
    ids = []
    for i, score_val in enumerate([60.0, 80.0, 70.0, 55.0], start=1):
        rid = pip_mod.upsert_role(_insert_role(f"https://example.com/job/{i}"))
        pip_mod.update_score_stage1(rid, score_val)
        ids.append((rid, score_val))

    top = pip_mod.get_top_n_for_deep_score(n=3)
    scores = [r["score_stage1"] for r in top]
    assert scores == sorted(scores, reverse=True), "must be ordered by score_stage1 DESC"
    assert len(top) == 3
    # None of them should have score_stage2 set
    assert all(r["score_stage2"] is None for r in top)


# ── Test 4: --deep-score 0 means _run_deep_score_prep is never called ────────


def test_deep_score_zero_skips_stage2(db, tmp_path):
    """When deep_score=0, no pending file is written."""
    import scripts.discover as discover_mod

    called = []

    def mock_prep(*args, **kwargs):
        called.append(True)

    with patch.object(discover_mod, "_run_deep_score_prep", side_effect=mock_prep):
        with patch("careerops.scraper.search_all_lanes", return_value=[]):
        # Simulate args with deep_score=0
            import argparse
            fake_args = argparse.Namespace(
                lane=None, limit=20, location=None, skip_filter=True,
                max_age_days=None, boards="linkedin,greenhouse,lever,ashby",
                companies=None, deep_score=0,
            )
            with patch("argparse.ArgumentParser.parse_args", return_value=fake_args):
                discover_mod.main()

    assert called == [], "_run_deep_score_prep must not be called when deep_score=0"


# ── Test 5: _run_deep_score_prep writes pending file with correct IDs ─────────


def test_run_deep_score_prep_writes_pending_file(db, tmp_path):
    for i in range(10):
        rid = pip_mod.upsert_role(_insert_role(f"https://example.com/job/{i}"))
        pip_mod.update_score_stage1(rid, 80.0 - i)

    import scripts.discover as discover_mod

    with patch("careerops.scraper.fetch_jd", return_value="<p>Senior TPM role…</p>"):
        with patch.object(pip_mod, "update_jd_raw"):
            discover_mod._run_deep_score_prep(n=5, lane=None, data_dir=tmp_path)

    pending_file = tmp_path / ".deep_score_pending.json"
    assert pending_file.exists(), "pending file must be written"
    data = json.loads(pending_file.read_text())
    assert "role_ids" in data
    assert len(data["role_ids"]) == 5
    assert "created_at" in data
    assert "discover_run_id" in data


# ── Test 6: update_jd_parsed sets jd_parsed_at ───────────────────────────────


def test_update_jd_parsed_sets_jd_parsed_at(db):
    rid = pip_mod.upsert_role(_insert_role())
    before = datetime.now(timezone.utc)
    pip_mod.update_jd_parsed(rid, {"required_skills": ["Go"], "comp_explicit": False})
    after = datetime.now(timezone.utc)

    role = pip_mod.get_role(rid)
    assert role["jd_parsed_at"] is not None
    # Timestamp is stored at second precision; check it falls within test window
    ts = datetime.fromisoformat(role["jd_parsed_at"].replace("Z", "+00:00"))
    before_s = before.replace(microsecond=0)
    after_s = after.replace(microsecond=0) + timedelta(seconds=1)
    assert before_s <= ts <= after_s


# ── Test 7: get_role returns COALESCE fit_score + _stage ─────────────────────


def test_get_role_returns_coalesced_fit_score_and_stage(db):
    rid = pip_mod.upsert_role(_insert_role())

    # Before any stage scores: _stage is S1
    role = pip_mod.get_role(rid)
    assert role["_stage"] == "S1"

    # After stage 1: fit_score = score_stage1, _stage = S1
    pip_mod.update_score_stage1(rid, 72.0)
    role = pip_mod.get_role(rid)
    assert role["fit_score"] == 72.0
    assert role["_stage"] == "S1"

    # After stage 2: fit_score = score_stage2, _stage = S2
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pip_mod.update_score_stage2(rid, 85.0, {}, ts)
    role = pip_mod.get_role(rid)
    assert role["fit_score"] == 85.0
    assert role["_stage"] == "S2"


# ── Test 8: update_score_stage2 overwrites prior stage-2 value ───────────────


def test_update_score_stage2_overwrites_prior_value(db):
    rid = pip_mod.upsert_role(_insert_role())
    pip_mod.update_score_stage1(rid, 70.0)

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pip_mod.update_score_stage2(rid, 77.0, {"v": 1}, ts)
    pip_mod.update_score_stage2(rid, 88.5, {"v": 2}, ts)

    role = pip_mod.get_role(rid)
    assert role["score_stage2"] == 88.5, "second update must overwrite the first"
    stored = json.loads(role["jd_parsed"])
    assert stored["v"] == 2
