"""Regression: SKILL.md onboarding section now points at modes/onboarding.md
and the prose 9-step list has been removed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "coin" / "SKILL.md"


def test_skill_md_exists():
    assert SKILL.exists()


def test_pointer_to_onboarding_mode():
    text = SKILL.read_text()
    assert "modes/onboarding.md" in text


def test_prose_onboarding_removed():
    text = SKILL.read_text()
    # The deleted prose markers — should NOT appear anywhere in SKILL.md
    forbidden = [
        "Drop a resume file path",
        "Use AskUserQuestion with options derived from the resume",
        "Be honest about CS-degree / FAANG-tour gaps that filter applications",
    ]
    for s in forbidden:
        assert s not in text, f"deleted prose still present: {s}"


def test_routing_table_has_setup_or_onboard():
    text = SKILL.read_text()
    assert "`setup`" in text and "modes/onboarding.md" in text
    assert "onboard" in text


def test_first_run_checklist_dispatches_onboarding():
    text = SKILL.read_text()
    # The First-Run Setup Checklist must reference modes/onboarding.md
    section = text.split("## First-Run Setup Checklist")[1].split("##")[0]
    assert "modes/onboarding.md" in section, "First-run checklist must dispatch onboarding"
