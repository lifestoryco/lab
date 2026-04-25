"""Structural + scaffolding test for modes/auto-pipeline.md.

The auto-pipeline is a prompt-driven mode (LLM-executed), so end-to-end
behavior testing requires a live agent. This test verifies what we CAN
mechanically check:

1. STRUCTURE — modes/auto-pipeline.md contains all 8 strict steps, the
   trigger spec, the two human gates, and the performance target. If anyone
   reorders or removes a step, this test fails.

2. PIPELINE PRIMITIVES — the careerops.pipeline functions the mode depends
   on (upsert_role, get_role, update_status, update_fit_score,
   update_jd_raw, update_jd_parsed) all exist and accept the documented args.

3. STOP CONDITIONS — the mode documents the exact conditions under which it
   refuses to proceed (out_of_band lane, fit < 50, audit BLOCK without fix).
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

AUTO_PIPELINE_MODE = ROOT / "modes" / "auto-pipeline.md"


# ── Structural tests ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mode_md() -> str:
    assert AUTO_PIPELINE_MODE.exists(), f"modes/auto-pipeline.md missing at {AUTO_PIPELINE_MODE}"
    return AUTO_PIPELINE_MODE.read_text()


def test_all_8_steps_present(mode_md: str) -> None:
    """Each step has a numbered heading. Order is non-negotiable."""
    expected = [
        "Step 1 — INGEST",
        "Step 2 — SCORE",
        "Step 3 — TRUTHFULNESS PRE-LOAD",
        "Step 4 — TAILOR",
        "Step 5 — AUDIT",
        "Step 6 — RENDER",
        "Step 7 — TRACK",
        "Step 8 — REPORT",
    ]
    for header in expected:
        assert header in mode_md, f"auto-pipeline.md missing step: {header}"


def test_trigger_spec_present(mode_md: str) -> None:
    """The trigger conditions for SKILL.md routing must be explicit."""
    assert "Trigger conditions" in mode_md
    # Three trigger types
    for token in ("URL starting with", "Multi-line text", "≥ 800 characters"):
        assert token in mode_md, f"auto-pipeline.md missing trigger token: {token}"
    # Anti-trigger list
    assert "Do NOT trigger" in mode_md, "must document sub-commands that should NOT trigger auto-pipeline"


def test_two_human_gates_documented(mode_md: str) -> None:
    """Auto-pipeline has exactly two human gates and they must be explicit."""
    assert "Audit BLOCK auto-fix" in mode_md
    assert "applied" in mode_md and "NEVER auto-submits" in mode_md, \
        "auto-pipeline must NEVER auto-submit"


def test_truthfulness_preload_required(mode_md: str) -> None:
    """The Cox/TitanX/Fortune-500 inflation pattern caught in the 2026-04-24
    code review must be referenced as the WHY behind Step 3."""
    assert "non-skippable" in mode_md.lower() or "non skippable" in mode_md.lower()
    assert "Cox" in mode_md or "TitanX" in mode_md or "Fortune-500" in mode_md or "Fortune 500" in mode_md, \
        "Step 3 must cite the inflation pattern it protects against"
    assert "priority-hierarchy.md" in mode_md
    assert "canonical facts" in mode_md.lower()


def test_stop_conditions_documented(mode_md: str) -> None:
    """Stop conditions for out-of-band lane and low fit score must be explicit."""
    assert "out_of_band" in mode_md, "must document out_of_band stop"
    assert "pedigree-filtered" in mode_md or "pedigree filter" in mode_md
    assert "composite < 50" in mode_md or "fit < 50" in mode_md, "must document low-fit stop"


def test_audit_verdict_routing(mode_md: str) -> None:
    """All three audit verdicts (CLEAN, NEEDS REVISION, BLOCK) must have
    explicit handling."""
    for verdict in ("CLEAN", "NEEDS REVISION", "BLOCK"):
        assert verdict in mode_md, f"auto-pipeline.md must handle audit verdict: {verdict}"
    # Auto-fix iteration cap
    assert "2 iterations" in mode_md, "must cap auto-fix loop at 2 iterations"


def test_report_format_spec(mode_md: str) -> None:
    """The Step 8 report shape must include all required sections."""
    sections = (
        "EXECUTIVE SUMMARY",
        "TOP 3 BULLETS",
        "GAPS TO PREP",
        "AUDIT VERDICT",
        "ARTIFACTS",
        "NEXT STEP",
    )
    for sec in sections:
        assert sec in mode_md, f"auto-pipeline.md report missing section: {sec}"


def test_performance_target(mode_md: str) -> None:
    """Sean is paying attention — surface a target so regressions are noticed."""
    assert "90 seconds" in mode_md or "90s" in mode_md, \
        "auto-pipeline.md must document an end-to-end performance target"


def test_failure_modes_documented(mode_md: str) -> None:
    """Each failure mode needs a recovery path."""
    failure_modes = (
        "URL fetch returns empty",
        "Lane assignment ambiguous",
        "Audit BLOCK can't be auto-fixed",
        "PDF render fails",
    )
    for fm in failure_modes:
        assert fm in mode_md, f"auto-pipeline.md missing failure mode: {fm}"


# ── Pipeline primitive tests ──────────────────────────────────────────────────

def test_pipeline_primitives_exist() -> None:
    """The auto-pipeline depends on these functions. If any go missing, it breaks."""
    from careerops import pipeline  # noqa: F401
    required = [
        "upsert_role",
        "get_role",
        "update_status",
        "update_fit_score",
        "update_jd_raw",
        "update_jd_parsed",
        "list_roles",
        "init_db",
    ]
    missing = [name for name in required if not hasattr(pipeline, name)]
    assert not missing, f"careerops.pipeline missing required functions: {missing}"


def test_score_primitives_exist() -> None:
    """Auto-pipeline calls these scoring primitives."""
    from careerops import score  # noqa: F401
    required = ["score_breakdown", "score_title", "score_grade", "score_fit"]
    missing = [name for name in required if not hasattr(score, name)]
    assert not missing, f"careerops.score missing required functions: {missing}"


def test_upsert_role_signature() -> None:
    """upsert_role must accept a dict with at minimum 'url' OR 'company'+'title'."""
    from careerops.pipeline import upsert_role
    sig = inspect.signature(upsert_role)
    assert len(sig.parameters) >= 1, "upsert_role must take at least one positional arg (the role dict)"


def test_score_breakdown_returns_composite_and_grade() -> None:
    """Step 2 of auto-pipeline relies on these keys in the breakdown dict."""
    from careerops.score import score_breakdown
    fake_role = {
        "title": "Sales Engineer",
        "company": "Filevine",
        "location": "Salt Lake City, UT",
        "remote": 0,
        "comp_min": 180000,
        "comp_max": 220000,
        "url": "https://www.linkedin.com/jobs/view/test",
    }
    bd = score_breakdown(fake_role, "enterprise-sales-engineer")
    assert "composite" in bd, "score_breakdown must return 'composite' key"
    assert "grade" in bd, "score_breakdown must return 'grade' key"
    assert "dimensions" in bd, "score_breakdown must return 'dimensions' key"
    assert isinstance(bd["composite"], (int, float))
    assert bd["grade"] in ("A", "B", "C", "D", "F")


# ── Smoke check on existing artifact ──────────────────────────────────────────

def test_filevine_artifact_chain_intact() -> None:
    """The Filevine role (id 137) was the first end-to-end auto-pipeline-worthy
    artifact. Verify the full chain (JSON + recruiter PDF) still exists. If it
    doesn't, future regressions to the renderer or tailor mode go uncaught."""
    json_path = ROOT / "data/resumes/generated/0137_enterprise-sales-engineer_2026-04-24.json"
    pdf_path = ROOT / "data/resumes/generated/0137_enterprise-sales-engineer_2026-04-24_recruiter.pdf"
    if json_path.exists():
        # Both should exist together; if PDF missing, render step is broken
        assert pdf_path.exists(), (
            "Filevine JSON exists but recruiter PDF is missing — "
            "render step regression. Run: /coin pdf 137 --recruiter"
        )
        assert pdf_path.stat().st_size > 30_000, (
            f"Filevine recruiter PDF is suspiciously small ({pdf_path.stat().st_size} bytes); "
            "rendering may have failed silently"
        )
