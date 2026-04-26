"""audit.md Check 10-14 — structural truthfulness gates documented.

These tests assert the mode-file structure (which checks exist + key
language present). The runtime behavior of each check is exercised in
test_score_panel.py (Check 10), test_linter.py (Check 11), test_parser.py
(Check 13), and test_render_resume.py (whole pipeline).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AUDIT_MD = (ROOT / "modes" / "audit.md").read_text()


def test_check_10_metric_outcome_present():
    assert "### Check 10 — Metric ↔ outcome row" in AUDIT_MD
    assert "truthfulness_gate" in AUDIT_MD
    assert "score_panel" in AUDIT_MD
    assert "structural" in AUDIT_MD.lower()


def test_check_11_buzzword_density():
    assert "### Check 11" in AUDIT_MD
    assert "buzzword" in AUDIT_MD.lower() or "kill-word" in AUDIT_MD.lower()
    assert "linter.py" in AUDIT_MD or "lint_resume" in AUDIT_MD
    assert "6.0%" in AUDIT_MD or "6%" in AUDIT_MD


def test_check_12_recruiter_eye():
    assert "### Check 12" in AUDIT_MD
    assert "recruiter-eye" in AUDIT_MD.lower()
    assert "30-sec" in AUDIT_MD or "30 second" in AUDIT_MD


def test_check_13_ats_parseability():
    assert "### Check 13" in AUDIT_MD
    assert "ats_score" in AUDIT_MD or "ATS parseability" in AUDIT_MD
    assert "parse_resume_pdf" in AUDIT_MD


def test_check_14_keyword_overlap():
    assert "### Check 14" in AUDIT_MD
    assert "Lightcast" in AUDIT_MD
    assert "keyword_overlap_pct" in AUDIT_MD
    assert "60-85%" in AUDIT_MD or "60–85%" in AUDIT_MD


def test_audit_advertises_14_checks():
    """Step 2 header should reflect 14 checks, not 9."""
    assert "Run the 14 audit checks" in AUDIT_MD


def test_audit_distinguishes_prose_from_structural():
    """Document that 1-9 are prose, 10-14 are structural."""
    assert "structural" in AUDIT_MD.lower()
    assert "prose-level" in AUDIT_MD.lower() or "Checks 1-9" in AUDIT_MD


def test_check_10_references_score_panel_helper():
    """Check 10's runtime helper must be named."""
    assert "careerops.score_panel.truthfulness_gate" in AUDIT_MD


def test_check_13_references_parser():
    assert "careerops.parser.parse_resume_pdf" in AUDIT_MD
