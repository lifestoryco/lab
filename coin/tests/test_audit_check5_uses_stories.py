"""Documentation tests for modes/audit.md Check 5 hardening."""
from pathlib import Path

AUDIT = Path(__file__).resolve().parent.parent / "modes" / "audit.md"


def _read():
    return AUDIT.read_text()


def test_check5_traces_story_ids():
    text = _read()
    assert "[story:" in text
    assert "get_story_by_id" in text or "stories.yml" in text


def test_check5_fails_on_unattributed_metrics():
    text = _read()
    # Look for the FAIL on unattributed metrics
    lower = text.lower()
    assert "unattributed" in lower
    assert "fail" in lower


def test_check5_warns_on_profile_only_attribution():
    text = _read()
    assert "[source:PROFILE]" in text
    assert "WARNING" in text or "WARN" in text or "warning" in text.lower()
