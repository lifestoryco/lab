"""Tests for careerops.levels — Levels.fyi seed lookup, imputation,
staleness; integration with score_comp and pipeline.upsert_role."""
from __future__ import annotations

import datetime as _dt
import os
from pathlib import Path

import pytest
import yaml

from careerops import levels as L


# ── shared seed fixture ────────────────────────────────────────────────

_TODAY = _dt.date.today().isoformat()
_OLD = (_dt.date.today() - _dt.timedelta(days=120)).isoformat()


def _seed_dict() -> dict:
    return {
        "companies": {
            "Filevine": {
                "last_refreshed": _TODAY,
                "source_url": "https://www.levels.fyi/companies/filevine/salaries",
                "levels": {
                    "L5": {
                        "base_p25": 145000, "base_p50": 165000, "base_p75": 185000,
                        "rsu_4yr_p50": 120000, "bonus_p50": 15000,
                    },
                    "staff": {
                        "base_p25": 175000, "base_p50": 195000, "base_p75": 220000,
                        "rsu_4yr_p50": 200000, "bonus_p50": 25000,
                    },
                },
            },
            "Datadog": {
                "last_refreshed": _TODAY,
                "source_url": "https://www.levels.fyi/companies/datadog/salaries",
                "levels": {
                    "L5": {
                        "base_p25": 246000, "base_p50": 246000, "base_p75": 246000,
                        "rsu_4yr_p50": 756000, "bonus_p50": 1400,
                    },
                },
            },
            "Stripe": {
                "last_refreshed": _OLD,
                "source_url": "https://www.levels.fyi/companies/stripe/salaries",
                "levels": {
                    "L5": {
                        "base_p25": 226000, "base_p50": 226000, "base_p75": 226000,
                        "rsu_4yr_p50": 696000, "bonus_p50": 15700,
                    },
                },
            },
            "HashiCorp": {
                "last_refreshed": _TODAY,
                "source_url": "https://www.levels.fyi/companies/hashicorp/salaries",
                "levels": {
                    "L5": {
                        "base_p25": 200000, "base_p50": 220000, "base_p75": 240000,
                        "rsu_4yr_p50": 320000, "bonus_p50": 0,
                    },
                },
            },
            "Acme Quantum Pickleball": {
                "last_refreshed": _TODAY,
                "source_url": "https://www.levels.fyi/",
                "unknown": True,
            },
        },
    }


@pytest.fixture
def patched_seed(tmp_path, monkeypatch):
    """Write a temporary seed file and redirect the loader at it."""
    seed_path = tmp_path / "levels_seed.yml"
    seed_path.write_text(yaml.safe_dump(_seed_dict(), sort_keys=False))
    monkeypatch.setattr(L, "_SEED_PATH", seed_path)
    L._reset_cache()
    yield seed_path
    L._reset_cache()


# ── 1. YAML structure ──────────────────────────────────────────────────

def test_yaml_loads_and_validates_structure(patched_seed):
    seed = L.load_levels_seed()
    assert isinstance(seed, dict)
    companies = seed.get("companies")
    assert isinstance(companies, dict)
    assert len(companies) >= 1
    for name, entry in companies.items():
        assert "last_refreshed" in entry, f"missing last_refreshed: {name}"
        assert "levels" in entry or entry.get("unknown") is True


# ── 2-7. lookup_company ────────────────────────────────────────────────

def test_lookup_company_exact_match(patched_seed):
    e = L.lookup_company("Filevine")
    assert e is not None
    assert "L5" in e["levels"]


def test_lookup_company_fuzzy_match_inc_stripped(patched_seed):
    e = L.lookup_company("Datadog, Inc.")
    assert e is not None
    assert e["levels"]["L5"]["base_p50"] == 246000


def test_lookup_company_fuzzy_match_lowercase(patched_seed):
    e = L.lookup_company("stripe")
    assert e is not None
    assert "L5" in e["levels"]


def test_lookup_company_one_direction_substring(patched_seed):
    """Seed key 'HashiCorp' inside 'HashiCorp Vault' should match.
    Reverse — 'Hash' inside seed 'HashiCorp' — must NOT match."""
    assert L.lookup_company("HashiCorp Vault") is not None
    assert L.lookup_company("Hash") is None


def test_lookup_company_miss_returns_none(patched_seed):
    assert L.lookup_company("Some Tiny Startup Inc") is None


def test_lookup_company_unknown_returns_none(patched_seed):
    """An entry with unknown:true returns None even on exact match."""
    assert L.lookup_company("Acme Quantum Pickleball") is None


# ── 8-10. impute_comp ──────────────────────────────────────────────────

def test_impute_comp_title_matches_staff_level(patched_seed):
    out = L.impute_comp("Filevine", "Staff Solutions Engineer")
    assert out is not None
    assert out["level_matched"] == "staff"
    assert out["confidence"] == 0.7
    assert out["comp_source"] == "imputed_levels"
    # base_p25 175K + rsu/4 (50K) + bonus 25K = 250K
    assert out["comp_min"] == 250000
    # base_p75 220K + 50K + 25K = 295K
    assert out["comp_max"] == 295000


def test_impute_comp_default_level_for_senior_title(patched_seed):
    out = L.impute_comp("Filevine", "Senior Sales Engineer")
    assert out is not None
    # No 'staff/principal/director/vp' hint → company default → L5
    assert out["level_matched"] == "L5"
    assert out["confidence"] == 0.5


def test_impute_comp_unknown_company_returns_none(patched_seed):
    assert L.impute_comp("Acme Quantum Pickleball", "Senior X") is None
    assert L.impute_comp("Tarantulas Inc", "Director") is None


# ── 11-12. score_comp behavior ─────────────────────────────────────────

def test_score_comp_imputed_applies_confidence_haircut(patched_seed):
    from careerops.score import score_comp, _raw_comp_score

    raw = _raw_comp_score(180000)
    expected = raw * (0.5 + 0.5 * 0.7)  # 85% of raw
    out = score_comp(180000, 220000, "imputed_levels", 0.7)
    assert abs(out - expected) < 0.01

    # Imputed must never beat verified at the same band.
    verified = score_comp(180000, 220000, "explicit", None)
    assert out < verified


def test_score_comp_unverified_returns_55(patched_seed):
    from careerops.score import score_comp
    assert score_comp(None, None, "unverified", None) == 55.0
    # Even when band IS present, unverified hard-caps at 55
    assert score_comp(180000, 220000, "unverified", None) == 55.0


# ── 13. pipeline auto-impute hook ──────────────────────────────────────

def test_upsert_role_auto_imputes_when_unverified(tmp_path, monkeypatch, patched_seed):
    """Insert an unverified Filevine role and assert it lands as
    imputed_levels with non-null comp_min/max + a notes audit trail."""
    db_path = tmp_path / "pipeline.db"
    monkeypatch.setenv("COIN_DB_PATH", str(db_path))
    # Bootstrap the DB schema fresh (m005..m007 add columns init_db expects)
    from scripts.migrations import (
        m005_posted_at as m005,
        m006_comp_currency as m006,
        m007_comp_confidence as m007,
    )
    from careerops import pipeline as p
    monkeypatch.setattr(p, "DB_PATH", str(db_path))
    p.init_db()
    # init_db's CREATE TABLE includes the new columns; migrations are no-ops here.

    role_id = p.upsert_role({
        "url": "https://example.com/jobs/filevine-1",
        "title": "Senior Solutions Engineer",
        "company": "Filevine",
        "location": "Lehi, UT",
        "comp_min": None,
        "comp_max": None,
        "comp_source": "unverified",
        "lane": "enterprise-sales-engineer",
    })

    row = p.get_role(role_id)
    assert row["comp_source"] == "imputed_levels"
    assert row["comp_min"] is not None
    assert row["comp_max"] is not None
    assert row["comp_confidence"] is not None
    assert "imputed comp from Levels.fyi seed" in (row.get("notes") or "")


# ── 14-15. get_seed_age ────────────────────────────────────────────────

def test_get_seed_age_returns_none_for_unknown_company(patched_seed):
    assert L.get_seed_age("Acme Pizza Co") is None


def test_get_seed_age_returns_days_for_known_company(patched_seed):
    assert L.get_seed_age("Filevine") == 0
    # Stripe was seeded 120 days ago in the fixture
    assert L.get_seed_age("Stripe") == 120


# ── 16. flag_stale ─────────────────────────────────────────────────────

def test_flag_stale_filters_by_threshold(patched_seed):
    stale_90 = L.flag_stale(90)
    assert "Stripe" in stale_90  # 120 > 90
    assert "Filevine" not in stale_90  # today
    # 200-day threshold filters out everything
    assert L.flag_stale(200) == []


# ── 17. lookup with company missing levels (edge case) ─────────────────

def test_lookup_company_missing_levels_returns_none(tmp_path, monkeypatch):
    seed = {
        "companies": {
            "BrokenCo": {
                "last_refreshed": _TODAY,
                # no levels key, no unknown flag — malformed
                "source_url": "https://x.example.com",
            },
        },
    }
    seed_path = tmp_path / "broken_seed.yml"
    seed_path.write_text(yaml.safe_dump(seed))
    monkeypatch.setattr(L, "_SEED_PATH", seed_path)
    L._reset_cache()
    assert L.lookup_company("BrokenCo") is None
    L._reset_cache()
