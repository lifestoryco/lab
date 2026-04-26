"""capture.md (STAR session) — mode-structure regression tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPTURE_MD = (ROOT / "modes" / "capture.md").read_text()


def test_capture_mode_file_exists():
    assert (ROOT / "modes" / "capture.md").exists()


def test_loads_shared_md_first():
    assert "Load `modes/_shared.md` first" in CAPTURE_MD


def test_step_0_loads_askuserquestion():
    assert "## Step 0" in CAPTURE_MD
    assert "ToolSearch" in CAPTURE_MD
    assert "AskUserQuestion" in CAPTURE_MD


def test_runs_migrations_first():
    assert "m005_experience_db.py" in CAPTURE_MD
    assert "m006_seed_lightcast.py" in CAPTURE_MD


def test_star_components_documented():
    """All four STAR components must be referenced."""
    for component in ("Situation", "Task", "Action", "Result"):
        assert component in CAPTURE_MD


def test_outcome_step_refuses_vague_claims():
    assert "vague" in CAPTURE_MD.lower()
    assert "significantly increased" in CAPTURE_MD or "vague claim" in CAPTURE_MD.lower()


def test_evidence_sources_enum_present():
    """All 4 evidence sources must be enumerated."""
    for source in ("self_reported", "manager_quoted", "system_exported", "public"):
        assert source in CAPTURE_MD


def test_seniority_ceiling_question_present():
    assert "seniority_ceiling" in CAPTURE_MD


def test_skill_tagger_uses_structured_output():
    assert "build_skill_tag_prompt" in CAPTURE_MD
    assert "validate_skill_tag_response" in CAPTURE_MD
    assert "SKILL_TAG_SCHEMA" in CAPTURE_MD


def test_lane_relevance_step_multiselect():
    assert "multiSelect: true" in CAPTURE_MD
    for lane in (
        "mid-market-tpm", "enterprise-sales-engineer",
        "iot-solutions-architect", "revenue-ops-operator",
    ):
        assert lane in CAPTURE_MD


def test_hard_refusals_present():
    refusals_section = CAPTURE_MD.split("## Hard refusals")[1].split("##")[0]
    # 5 hard refusals expected.
    assert refusals_section.count("|") >= 12  # rough — table cells
