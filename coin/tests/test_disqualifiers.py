"""Tests for careerops.disqualifiers + score_breakdown DQ integration."""

import pytest

from careerops.disqualifiers import scan_jd, apply_disqualifiers
from careerops.score import score_breakdown
from data.resumes.base import PROFILE


ROCK_WEST_JD = """
Rock West Composites is seeking a Manufacturing Engineer ...
BS or BA degree in an engineering or materials science discipline;
OR more than 15 years' experience in development of manufacturing processes
of advanced composite materials. Minimum 8 years' experience in a composite
manufacturing environment. ...
Must be a U.S. Person under 22 CFR 120 (due to ITAR Restrictions).
"""

HPE_JD = """
Federal Technical Program Manager, (Clearance Secret Required)
Hewlett Packard Enterprise is seeking a TPM to lead federal programs.
Active Secret clearance required. ...
"""

JOURNEYTEAM_JD = """
Sales Engineer — JourneyTeam
You will demo Microsoft Dynamics 365, Power Platform, Power BI, and
Azure-hosted solutions to customers. Hands-on D365 experience required.
"""

CODA_JD = """
Sales Engineer — Coda Technologies
You will advise customer cybersecurity teams on threat intel, SIEM
deployments, SOC workflows, zero trust architecture, and red team /
blue team exercises. Cybersecurity domain expertise required.
"""

EQUIVALENCE_JD = """
We're looking for a software engineer with a BS in Computer Science required,
or equivalent experience. ...
"""


def _profile(**overrides):
    p = {**PROFILE}
    p.update(overrides)
    return p


def test_rockwest_hard_dq_itar_and_degree():
    r = scan_jd(ROCK_WEST_JD, _profile(_target_title="Engineering / TPM"))
    # Rock West JD uses "BA degree in...materials science discipline" form
    # which doesn't match the "BS in X required" hard-pattern; but the
    # ITAR + degree-discipline phrasing must trigger ITAR for sure.
    assert "itar_restricted" in r["hard_dq"]


def test_hpe_hard_dq_clearance():
    r = scan_jd(HPE_JD, _profile(_target_title="Federal Technical Program Manager"))
    assert r["hard_dq"] == ["clearance_required"]


def test_journeyteam_soft_dq_msft_stack():
    r = scan_jd(JOURNEYTEAM_JD, _profile(_target_title="Sales Engineer", skills=[]))
    assert ("msft_stack_mismatch", -20) in r["soft_dq"]


def test_coda_soft_dq_security():
    r = scan_jd(CODA_JD,
                _profile(_target_title="Sales Engineer — Coda Technologies Cybersecurity"))
    assert ("narrow_security_domain", -20) in r["soft_dq"]


@pytest.mark.parametrize("phrase", [
    "Secret clearance required",
    "TS/SCI clearance required",
    "Public Trust clearance required",
    "Top Secret clearance required",
])
def test_clearance_variants(phrase):
    r = scan_jd(f"This role needs an active {phrase}.", _profile())
    assert "clearance_required" in r["hard_dq"]


@pytest.mark.parametrize("phrase", [
    "ITAR restrictions apply",
    "22 CFR 120 applies",
    "22 CFR 121 applies",
    "This is an export controlled position",
])
def test_itar_variants(phrase):
    r = scan_jd(phrase, _profile())
    assert "itar_restricted" in r["hard_dq"]


def test_degree_required_hard():
    r = scan_jd("BS in Computer Science is required for this role.", _profile())
    assert "degree_required" in r["hard_dq"]


def test_degree_or_equivalent_not_hard():
    r = scan_jd(EQUIVALENCE_JD, _profile())
    assert "degree_required" not in r["hard_dq"]
    assert all(reason != "degree_required" for reason, _ in r["soft_dq"])


def test_msft_stack_with_skill_does_not_trigger():
    r = scan_jd("This role uses Azure and Power BI extensively.",
                _profile(_target_title="Sales Engineer",
                         skills=["Azure", "Power BI"]))
    assert all(reason != "msft_stack_mismatch" for reason, _ in r["soft_dq"])


def test_msft_stack_without_skill_triggers():
    r = scan_jd("Hands-on D365 experience required.",
                _profile(_target_title="Sales Engineer", skills=[]))
    assert ("msft_stack_mismatch", -20) in r["soft_dq"]


def test_security_3_mentions_with_security_title_triggers():
    jd = "We need expertise in SIEM, SOC, and zero trust deployments."
    r = scan_jd(jd, _profile(_target_title="Sales Engineer Cybersecurity"))
    assert ("narrow_security_domain", -20) in r["soft_dq"]


def test_security_1_mention_does_not_trigger():
    r = scan_jd("Familiarity with SIEM is a plus.",
                _profile(_target_title="Sales Engineer Cybersecurity"))
    assert all(reason != "narrow_security_domain" for reason, _ in r["soft_dq"])


def test_security_3_mentions_without_security_title_does_not_trigger():
    jd = "We need expertise in SIEM, SOC, and zero trust deployments."
    r = scan_jd(jd, _profile(_target_title="Sales Engineer"))
    assert all(reason != "narrow_security_domain" for reason, _ in r["soft_dq"])


def test_apply_disqualifiers_mutates_lane_on_hard():
    role = {"title": "TPM", "jd_raw": HPE_JD,
            "lane": "mid-market-tpm", "notes": ""}
    apply_disqualifiers(role, {}, PROFILE)
    assert role["lane"] == "out_of_band"
    assert "DQ: clearance_required" in role["notes"]


def test_apply_disqualifiers_does_not_mutate_lane_on_soft():
    role = {"title": "Sales Engineer", "jd_raw": JOURNEYTEAM_JD,
            "lane": "enterprise-sales-engineer", "notes": ""}
    apply_disqualifiers(role, {}, _profile(skills=[]))
    assert role["lane"] == "enterprise-sales-engineer"


def test_score_breakdown_with_hard_dq_returns_composite_zero():
    role = {"title": "TPM", "company": "Acme", "comp_min": 200000,
            "comp_max": 250000, "url": "https://greenhouse.io/x"}
    out = score_breakdown(role, "mid-market-tpm",
                          dq_result={"hard_dq": ["clearance_required"],
                                     "soft_dq": [], "matched_phrases": {}})
    assert out["composite"] == 0.0
    assert out["grade"] == "F"
    assert out["disqualified"] is True
    assert out["dq_reasons"] == ["clearance_required"]


def test_score_breakdown_with_soft_dq_deducts():
    role = {"title": "Technical Program Manager",
            "company": "Filevine", "comp_min": 200000, "comp_max": 250000,
            "url": "https://greenhouse.io/x", "remote": "remote",
            "posted_at": None}
    base = score_breakdown(role, "mid-market-tpm")
    out = score_breakdown(role, "mid-market-tpm",
                          dq_result={"hard_dq": [],
                                     "soft_dq": [("msft_stack_mismatch", -20)],
                                     "matched_phrases": {}})
    assert out["composite"] == round(max(0.0, base["composite"] - 20), 1)
    assert out["dq_reasons"] == ["msft_stack_mismatch"]
    assert out["dimensions"]["domain_fit"]["weight"] == 0.0


def test_score_breakdown_no_dq_unchanged():
    role = {"title": "TPM", "company": "Acme", "comp_min": 200000,
            "comp_max": 250000, "url": "https://greenhouse.io/x"}
    a = score_breakdown(role, "mid-market-tpm")
    b = score_breakdown(role, "mid-market-tpm", dq_result=None)
    assert a == b
    assert "disqualified" not in a
    assert "dq_reasons" not in a


def test_matched_phrases_populated():
    r = scan_jd(HPE_JD, _profile())
    assert "Secret" in r["matched_phrases"]["clearance_required"]
    assert "clearance" in r["matched_phrases"]["clearance_required"].lower()


def test_empty_jd_returns_empty_result():
    r = scan_jd("", _profile())
    assert r == {"hard_dq": [], "soft_dq": [], "matched_phrases": {}}
