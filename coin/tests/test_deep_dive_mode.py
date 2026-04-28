"""Documentation tests for modes/deep-dive.md and SKILL.md routing."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEEP_DIVE = REPO / "modes" / "deep-dive.md"
SKILL = REPO / ".claude" / "skills" / "coin" / "SKILL.md"


def _read_deep_dive() -> str:
    assert DEEP_DIVE.exists(), "modes/deep-dive.md must exist"
    return DEEP_DIVE.read_text()


def test_deep_dive_md_exists():
    assert DEEP_DIVE.exists()


def test_deep_dive_loads_askuserquestion_in_step_0():
    text = _read_deep_dive()
    assert "ToolSearch" in text
    assert "select:AskUserQuestion" in text


def test_deep_dive_uses_stories_yml_and_add_story():
    text = _read_deep_dive()
    assert "stories.yml" in text
    assert "add_story" in text


def test_deep_dive_mentions_probe_questions():
    text = _read_deep_dive().lower()
    for needle in ("dollar number", "team", "artifact", "lanes", "grade"):
        assert needle in text, f"missing probe topic: {needle}"


def test_deep_dive_mentions_validation_against_existing_stories():
    text = _read_deep_dive()
    assert "find_stories_for_skills" in text
    assert "duplicate" in text.lower() or "Duplicate" in text


def test_deep_dive_named_account_ok_options():
    text = _read_deep_dive()
    assert "named_account_ok" in text or "client/company name" in text
    for option in ("Yes", "No", "Needs permission"):
        assert option in text


def test_deep_dive_atomic_write_pattern():
    text = _read_deep_dive().lower()
    assert "atomic" in text


def test_skill_md_routes_deep_dive():
    text = SKILL.read_text()
    assert "deep-dive" in text
    assert "modes/deep-dive.md" in text
