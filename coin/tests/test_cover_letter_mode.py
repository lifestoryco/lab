"""Structural tests for modes/cover-letter.md."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODE = ROOT / "modes" / "cover-letter.md"


@pytest.fixture(scope="module")
def mode_text() -> str:
    return MODE.read_text()


def test_mode_file_exists():
    assert MODE.exists()


def test_steps_present(mode_text):
    for n in range(1, 8):
        assert f"## Step {n}" in mode_text, f"Step {n} missing"


def test_three_paragraph_structure_with_word_budgets(mode_text):
    assert "Hook (≤ 80 words)" in mode_text
    assert "Proof (≤ 130 words)" in mode_text
    assert "Fit (≤ 70 words)" in mode_text
    assert "280 words" in mode_text


def test_refusals_documented(mode_text):
    for refusal in [
        "Generating a cover letter without a tailored resume JSON",
        "Citing a metric not in",
        "Claiming Cox/TitanX/Safeguard outcomes",
        "I am writing to apply for",
        "Exceeding 280 words",
        "audit_passes: true",
        "CS / engineering degree",
    ]:
        assert refusal in mode_text, f"refusal not documented: {refusal}"


def test_truthfulness_gate_referenced(mode_text):
    assert "_shared.md" in mode_text
    assert "Operating Principle #3" in mode_text


def test_story_parity_check_documented(mode_text):
    assert "stories_used" in mode_text
    assert "subset" in mode_text


def test_jd_keyword_parity_check_documented(mode_text):
    assert "jd_keywords_cited" in mode_text
    assert "substrings" in mode_text


def test_audit_subset_documented(mode_text):
    # Cover audit reuses audit.md's 5 CRITICAL truthfulness checks
    # (Check 1 Education, 2 Pedigree, 3 Cox/TitanX/Safeguard, 4 Vague-flex,
    # 5 Metric provenance); skips Checks 6-9 which are resume-specific.
    for label in (
        "Check 1 — Education truthfulness",
        "Check 2 — Pedigree non-claim",
        "Check 3 — Cox/TitanX/Safeguard attribution",
        "Check 4 — Vague-flex qualifiers",
        "Check 5 — Metric provenance",
    ):
        assert label in mode_text, f"audit-subset label missing: {label}"
    # Confirm Checks 6-9 are explicitly skipped, not silently dropped
    assert "Checks 6–9" in mode_text or "Checks 6-9" in mode_text


def test_render_refuses_unaudited(mode_text):
    assert "refuse to render" in mode_text or "refuses to render" in mode_text
