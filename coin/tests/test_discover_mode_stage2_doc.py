"""Structural regression tests for modes/discover.md Step 4a.

These guard against future edits that silently break the agent contract:
the deep-score loop prompt block must remain verbatim so the executing
Claude Code session has the exact JD-parsing schema.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_DISCOVER_MD = Path(__file__).resolve().parent.parent / "modes" / "discover.md"


def _content() -> str:
    return _DISCOVER_MD.read_text()


def test_discover_md_contains_step_4a():
    """Step 4a header must be present — the agent looks for it to know when
    to start the deep-score loop."""
    assert "Step 4a — Deep-score" in _content(), (
        "modes/discover.md must contain 'Step 4a — Deep-score'"
    )


def test_discover_md_contains_jd_parse_prompt_block():
    """The verbatim JD-parsing prompt block must be intact so the executing
    Claude Code session has the exact schema to extract into JSON."""
    content = _content()
    assert "required_skills: list[str]" in content, (
        "modes/discover.md must contain 'required_skills: list[str]' "
        "from the JD-parsing prompt block"
    )
    assert "Output ONLY the JSON object" in content, (
        "modes/discover.md must contain 'Output ONLY the JSON object' "
        "to prevent the agent from adding prose around the output"
    )
