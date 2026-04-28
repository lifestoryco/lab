"""Documentation tests for modes/tailor.md stories.yml integration."""
from pathlib import Path

TAILOR = Path(__file__).resolve().parent.parent / "modes" / "tailor.md"


def _read():
    return TAILOR.read_text()


def test_tailor_uses_find_stories_for_skills():
    assert "find_stories_for_skills" in _read()


def test_tailor_documents_story_id_attribution_syntax():
    text = _read()
    assert "[story:" in text
    assert "audit Check 5" in text


def test_tailor_documents_grade_preference():
    text = _read()
    # A > B > C ordering in the rank rules
    assert ("Grade A" in text or "A > B > C" in text)
