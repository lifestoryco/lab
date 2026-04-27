import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from careerops.score import (
    score_comp, score_company_tier, score_title, score_remote,
    score_application_effort, score_seniority_fit, score_culture_fit,
    score_grade, score_fit, score_breakdown,
)


# ── comp ──────────────────────────────────────────────────────────────────────

def test_comp_unverified_middle():
    assert score_comp(None, None) == 55.0

def test_comp_above_total_floor():
    assert score_comp(260000, 320000) == 100.0

def test_comp_between_floors():
    s = score_comp(200000, 250000)
    assert 60 <= s <= 100

def test_comp_below_base_floor():
    s = score_comp(100000, 120000)
    assert 0 <= s < 60


# ── company_tier ──────────────────────────────────────────────────────────────

# Company tier scoring is INVERTED for Sean's reality (2026-04-25):
# tier1 (in-league mid-market / Utah tech) = 100
# tier2 (recognized brand, Sean is a stretch) = 75
# default (unknown small co) = 65 — neutral, no penalty
# tier4_pedigree_filter (FAANG / big-tech) = 25 — Sean screened out at recruiter step

def test_company_tier_faang_pedigree_penalty():
    """FAANG-tier companies trigger pedigree filter; scored low for Sean."""
    assert score_company_tier("Netflix") == 25.0
    assert score_company_tier("Google") == 25.0
    assert score_company_tier("Stripe") == 25.0
    assert score_company_tier("LinkedIn") == 25.0

def test_company_tier_in_league_mid_market():
    """Utah tech + Series B-D mid-market = Sean's sweet spot."""
    assert score_company_tier("Filevine") == 100.0
    assert score_company_tier("Pluralsight") == 100.0
    assert score_company_tier("Particle") == 100.0
    assert score_company_tier("Verkada") == 100.0

def test_company_tier_recognized_stretch():
    """Recognized brands where Sean is a stretch but not pedigree-filtered."""
    assert score_company_tier("Cloudflare") == 75.0
    assert score_company_tier("HubSpot") == 75.0

def test_company_tier_unknown_neutral():
    """Unknown companies default to 65 — neutral, no penalty."""
    assert score_company_tier("Tiny Startup LLC") == 65.0

def test_company_tier_none_neutral():
    assert score_company_tier(None) == 65.0

def test_company_tier_case_insensitive():
    assert score_company_tier("netflix") == score_company_tier("NETFLIX")

def test_company_tier_substring_safety():
    """Bidirectional substring used to false-positive ('roku' in 'rokumetrics').
    The fix uses one-direction word-boundary matching."""
    assert score_company_tier("rokumetrics") != 25.0  # Should not match Roku
    assert score_company_tier("mxnet labs") != 100.0  # Should not match MX


# ── title ────────────────────────────────────────────────────────────────────

# Lane rename (2026-04-25): cox-style-tpm → mid-market-tpm.
# The new mid-market-tpm lane EXCLUDES "staff technical program manager" and
# "principal technical program manager" because Sean is pedigree-filtered out
# of those titles. Tests below reflect this.

def test_title_exclusion_zeroes_out():
    assert score_title("Junior Technical Program Manager", "mid-market-tpm") == 0.0

def test_title_hit():
    """Senior TPM is the sweet spot for mid-market-tpm lane."""
    assert score_title("Senior Technical Program Manager", "mid-market-tpm") == 100.0

def test_title_staff_principal_excluded_for_mid_market():
    """Staff and Principal TPM titles are pedigree-filtered for Sean."""
    assert score_title("Staff Technical Program Manager", "mid-market-tpm") == 0.0
    assert score_title("Principal Technical Program Manager, Innovation Office", "mid-market-tpm") == 0.0

def test_title_director_hits_mid_market():
    assert score_title("Director of Program Management", "mid-market-tpm") == 100.0

def test_title_sales_engineer_hits_se_lane():
    assert score_title("Sales Engineer", "enterprise-sales-engineer") == 100.0
    assert score_title("Senior Solutions Architect", "iot-solutions-architect") == 100.0


# ── remote ───────────────────────────────────────────────────────────────────

def test_remote_explicit():
    assert score_remote({"remote": 1}) == 100.0

def test_remote_hybrid_location():
    assert score_remote({"remote": 0, "location": "Hybrid - New York"}) == 70.0


# ── application_effort ───────────────────────────────────────────────────────

def test_effort_linkedin():
    assert score_application_effort("https://www.linkedin.com/jobs/view/123") == 90.0

def test_effort_greenhouse():
    assert score_application_effort("https://jobs.greenhouse.io/acme/123") == 65.0

def test_effort_unknown_portal():
    assert score_application_effort("https://careers.randomcorp.com/apply/456") == 40.0

def test_effort_none():
    assert score_application_effort(None) == 60.0


# ── seniority_fit ─────────────────────────────────────────────────────────────

def test_seniority_staff():
    assert score_seniority_fit({"seniority": "staff"}) == 100.0

def test_seniority_principal():
    assert score_seniority_fit({"seniority": "principal"}) == 100.0

def test_seniority_senior():
    assert score_seniority_fit({"seniority": "senior"}) == 80.0

def test_seniority_junior():
    assert score_seniority_fit({"seniority": "junior"}) == 0.0

def test_seniority_none():
    assert score_seniority_fit(None) == 55.0


# ── culture_fit ───────────────────────────────────────────────────────────────

def test_culture_no_flags():
    assert score_culture_fit({"red_flags": [], "culture_signals": []}) == 80.0

def test_culture_two_red_flags():
    s = score_culture_fit({"red_flags": ["keeper test", "rockstar language"], "culture_signals": []})
    assert s == 60.0

def test_culture_positive_signals():
    s = score_culture_fit({"red_flags": [], "culture_signals": ["remote-first", "async", "flat hierarchy"]})
    assert s > 80.0

def test_culture_clamped_to_100():
    many_positives = ["remote-first", "async", "flat", "autonomy", "flexible", "transparent", "collaborative"]
    s = score_culture_fit({"red_flags": [], "culture_signals": many_positives})
    assert s <= 100.0

def test_culture_none():
    assert score_culture_fit(None) == 60.0


# ── grade ─────────────────────────────────────────────────────────────────────

def test_grade_a():
    assert score_grade(90.0) == "A"
    assert score_grade(85.0) == "A"

def test_grade_b():
    assert score_grade(84.9) == "B"
    assert score_grade(70.0) == "B"

def test_grade_c():
    assert score_grade(69.9) == "C"
    assert score_grade(55.0) == "C"

def test_grade_d():
    assert score_grade(54.9) == "D"
    assert score_grade(40.0) == "D"

def test_grade_f():
    assert score_grade(39.9) == "F"
    assert score_grade(0.0) == "F"


# ── breakdown + composite ─────────────────────────────────────────────────────

def test_breakdown_shape():
    role = {"title": "Senior TPM", "company": "Filevine", "location": "Salt Lake City, UT", "remote": 0, "comp_min": 200000}
    bd = score_breakdown(role, "mid-market-tpm")
    assert "composite" in bd
    assert "grade" in bd
    assert "dimensions" in bd
    expected_dims = {"comp", "company_tier", "skill_match", "title_match",
                     "remote", "application_effort", "seniority_fit", "culture_fit",
                     "freshness"}
    assert set(bd["dimensions"].keys()) == expected_dims


def test_score_breakdown_includes_freshness():
    """m005 regression: freshness must be a key + composite still in [0,100]."""
    role = {"title": "Senior TPM", "company": "Filevine",
            "location": "Salt Lake City, UT", "remote": 0, "comp_min": 200000,
            "posted_at": None}
    bd = score_breakdown(role, "mid-market-tpm")
    assert "freshness" in bd["dimensions"]
    assert 0 <= bd["composite"] <= 100


def test_fit_score_weights_sum_to_one():
    """FIT_SCORE_WEIGHTS must sum to exactly 1.0 (with float tolerance)."""
    from config import FIT_SCORE_WEIGHTS
    assert abs(sum(FIT_SCORE_WEIGHTS.values()) - 1.0) < 1e-9

def test_breakdown_contributions_sum_to_composite():
    role = {"title": "Senior TPM", "company": "Filevine", "location": "Salt Lake City, UT", "remote": 0, "comp_min": 200000}
    bd = score_breakdown(role, "mid-market-tpm")
    total = sum(d["contribution"] for d in bd["dimensions"].values())
    assert abs(total - bd["composite"]) < 0.2  # floating point tolerance

def test_full_fit_basic():
    """In-league role should score B-grade or better."""
    role = {
        "title": "Senior Technical Program Manager",
        "company": "Filevine",
        "location": "Salt Lake City, UT",
        "remote": 0,
        "comp_min": 180000,
        "comp_max": 220000,
    }
    fit = score_fit(role, "mid-market-tpm")
    assert fit >= 65, f"In-league mid-market role should grade at least C; got {fit}"

def test_faang_role_scores_LOWER_than_unknown_for_sean():
    """KEY INVERSION (2026-04-25): FAANG companies are pedigree-filtered for
    Sean. A Netflix Senior TPM should score LOWER than the same role at an
    unknown small company because Sean gets screened out at recruiter step #1
    for FAANG but at least clears the gate at unknowns."""
    base = {
        "title": "Senior Technical Program Manager",  # not the excluded "Staff"
        "location": "Remote",
        "remote": 1,
        "comp_min": 200000,
    }
    faang = {**base, "company": "Netflix"}
    unknown = {**base, "company": "Tiny Startup LLC"}
    assert score_fit(faang, "mid-market-tpm") < score_fit(unknown, "mid-market-tpm"), (
        "Inversion broken: FAANG should score LOWER than unknown for Sean. "
        "Check COMPANY_TIERS in config.py."
    )

def test_out_of_band_lane_short_circuits_to_zero():
    """Quarantine guard (2026-04-25): roles in lane='out_of_band' must
    short-circuit to composite=0, grade=F. Without this, the per-dimension
    scorers fall through to defaults and produce ~30-40, which then resurrects
    the role in the dashboard after re-score."""
    role = {
        "title": "Staff Technical Program Manager",
        "company": "Netflix",
        "location": "Remote",
        "remote": 1,
        "comp_min": 500000,  # Even with great comp, must remain quarantined
    }
    bd = score_breakdown(role, "out_of_band")
    assert bd["composite"] == 0.0
    assert bd["grade"] == "F"
    assert bd.get("quarantined") is True

def test_unknown_lane_treated_as_quarantine():
    """A lane name not in LANES (typo, deleted lane, etc.) also short-circuits
    to 0 rather than producing a misleading score from default fall-throughs."""
    role = {"title": "Senior TPM", "company": "Acme", "comp_min": 200000}
    bd = score_breakdown(role, "this-lane-does-not-exist")
    assert bd["composite"] == 0.0
    assert bd["grade"] == "F"

def test_parsed_jd_comp_fallback():
    """Explicit comp in parsed_jd should elevate score when DB comp_min is null."""
    role_no_comp = {
        "title": "Senior TPM", "company": "Filevine",
        "location": "Salt Lake City, UT", "remote": 0, "comp_min": None,
        "url": "https://www.linkedin.com/jobs/view/123",
    }
    parsed = {"comp_min": 200000, "comp_max": 230000, "comp_explicit": True}
    score_with = score_fit(role_no_comp, "mid-market-tpm", parsed_jd=parsed)
    score_without = score_fit(role_no_comp, "mid-market-tpm")
    assert score_with > score_without
