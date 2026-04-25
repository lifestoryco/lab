"""Structural tests for modes/onboarding.md."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODE = ROOT / "modes" / "onboarding.md"


@pytest.fixture(scope="module")
def mode_text() -> str:
    return MODE.read_text()


def test_mode_file_exists():
    assert MODE.exists()


def test_step_0_loads_askuserquestion(mode_text):
    assert "## Step 0" in mode_text
    assert "select:AskUserQuestion" in mode_text


def test_question_count_consistent(mode_text):
    """Header, walked steps, and summary line must all agree on the count.
    Regression: previously said '9 deterministic' / 'all 8 answers' / 7
    actual capture steps."""
    # Normalize all whitespace runs to single spaces for prose-wrap tolerance
    normalized = " ".join(mode_text.split())
    assert "through 7 deterministic AskUserQuestion blocks" in normalized
    assert "summary of all 7 captured answers" in normalized
    # Old counts must be gone
    assert "9 deterministic" not in normalized
    assert "all 8 answers" not in normalized


def test_safety_gate_at_top(mode_text):
    assert "## Step 1" in mode_text
    assert "Re-onboard from scratch" in mode_text
    assert '"Yes, replace"' in mode_text
    assert '"Update specific fields only"' in mode_text
    assert '"Cancel"' in mode_text


def test_targeted_field_update_branch(mode_text):
    assert "## Step 1.5" in mode_text or "Step 1.5" in mode_text
    assert "multiSelect: true" in mode_text


def test_all_9_questions_present(mode_text):
    """Step 2 → Question 1 ... Step 9 → save. Each labeled."""
    for n in range(2, 10):
        assert f"## Step {n}" in mode_text, f"Step {n} missing"
    # Each captures one of the 7 question labels
    for label in [
        "Question 1", "Question 2", "Question 3", "Question 4",
        "Question 5", "Question 6", "Question 7",
    ]:
        assert label in mode_text, f"label missing: {label}"


def test_each_askuserquestion_specifies_options(mode_text):
    # Count question/options pairs
    askuserquestion_blocks = mode_text.count("AskUserQuestion")
    options_blocks = mode_text.count("options:")
    # Step 7 (comp) is intentionally free-text — so blocks-with-options ≥ 6
    assert options_blocks >= 6, f"expected ≥ 6 question blocks with options, got {options_blocks}"
    assert askuserquestion_blocks >= 7


def test_multiselect_explicit_where_needed(mode_text):
    # Locations + industries + targeted-field-update branch use multiSelect
    assert mode_text.count("multiSelect: true") >= 3


def test_pedigree_question_load_bearing(mode_text):
    assert "Pedigree" in mode_text or "pedigree" in mode_text
    assert "Filtered out" in mode_text
    assert "pedigree_constraint" in mode_text
    assert "load-bearing" in mode_text


def test_refusals_documented(mode_text):
    for refusal in [
        "Overwriting an existing",
        "Inferring `pedigree_constraint`",
        "Writing `positions`",
        "Skipping any of the 9 questions",
        "Auto-running discover at scale",
    ]:
        assert refusal in mode_text, f"refusal not documented: {refusal}"


def test_save_writes_only_identity_slice(mode_text):
    # Mode owns: name, email, phone, city, state, linkedin, target_locations, target_archetypes
    # NOT: positions, education, skills_grid, cert_grid
    assert "name`, `email`, `phone`, `city`, `state`, `linkedin`" in mode_text
    assert "positions" in mode_text
    assert "manual edits" in mode_text or "manual-edit" in mode_text


def test_atomic_write_protocol(mode_text):
    assert "profile.staging.yml" in mode_text
    assert "yaml.safe_load" in mode_text
    assert "Atomically replace" in mode_text


def test_completion_marker(mode_text):
    assert "data/onboarding/.completed" in mode_text


def test_smoke_discovery_capped_at_5(mode_text):
    assert "--limit 5" in mode_text
