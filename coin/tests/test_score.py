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

def test_company_tier_faang():
    assert score_company_tier("Netflix") == 100.0
    assert score_company_tier("Google") == 100.0
    assert score_company_tier("Stripe") == 100.0

def test_company_tier_growth():
    assert score_company_tier("Roku") == 75.0
    assert score_company_tier("Cloudflare") == 75.0

def test_company_tier_unknown():
    s = score_company_tier("Tiny Startup LLC")
    assert s == 45.0

def test_company_tier_none():
    assert score_company_tier(None) == 45.0

def test_company_tier_case_insensitive():
    assert score_company_tier("netflix") == score_company_tier("NETFLIX")


# ── title ────────────────────────────────────────────────────────────────────

def test_title_exclusion_zeroes_out():
    assert score_title("Junior Technical Program Manager", "cox-style-tpm") == 0.0

def test_title_hit():
    assert score_title("Staff Technical Program Manager", "cox-style-tpm") == 100.0


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
    role = {"title": "Staff TPM", "company": "Netflix", "location": "Remote", "remote": 1, "comp_min": 420000}
    bd = score_breakdown(role, "cox-style-tpm")
    assert "composite" in bd
    assert "grade" in bd
    assert "dimensions" in bd
    expected_dims = {"comp", "company_tier", "skill_match", "title_match",
                     "remote", "application_effort", "seniority_fit", "culture_fit"}
    assert set(bd["dimensions"].keys()) == expected_dims

def test_breakdown_contributions_sum_to_composite():
    role = {"title": "Staff TPM", "company": "Netflix", "location": "Remote", "remote": 1, "comp_min": 420000}
    bd = score_breakdown(role, "cox-style-tpm")
    total = sum(d["contribution"] for d in bd["dimensions"].values())
    assert abs(total - bd["composite"]) < 0.2  # floating point tolerance

def test_full_fit_basic():
    role = {
        "title": "Staff Technical Program Manager",
        "company": "Acme",
        "location": "Remote, United States",
        "remote": 1,
        "comp_min": 220000,
        "comp_max": 290000,
    }
    fit = score_fit(role, "cox-style-tpm")
    assert fit >= 65

def test_faang_role_scores_higher_than_unknown():
    base = {
        "title": "Staff Technical Program Manager",
        "location": "Remote",
        "remote": 1,
        "comp_min": 300000,
    }
    faang = {**base, "company": "Netflix"}
    unknown = {**base, "company": "Tiny Startup LLC"}
    assert score_fit(faang, "cox-style-tpm") > score_fit(unknown, "cox-style-tpm")

def test_parsed_jd_comp_fallback():
    """Explicit comp in parsed_jd should elevate score when DB comp_min is null."""
    role_no_comp = {
        "title": "Staff TPM", "company": "Netflix",
        "location": "Remote", "remote": 1, "comp_min": None,
        "url": "https://www.linkedin.com/jobs/view/123",
    }
    parsed = {"comp_min": 420000, "comp_max": 630000, "comp_explicit": True}
    score_with = score_fit(role_no_comp, "cox-style-tpm", parsed_jd=parsed)
    score_without = score_fit(role_no_comp, "cox-style-tpm")
    assert score_with > score_without
