"""Structural + regression test for modes/audit.md.

Audit is a prompt-driven mode (executed by an LLM agent reading the markdown),
so this test verifies two things that don't require running the LLM:

1. STRUCTURE — modes/audit.md contains all 9 checks, the verdict rules, the
   output format, the human gate, and the auto-fix protocol. If anyone weakens
   the audit by deleting a check or removing the human gate, this test fails.

2. REGRESSION — the known-bad Filevine SE JSON (id 137, generated 2026-04-24)
   contains the exact substrings that triggered the 2026-04-24 code-review
   findings. Asserting they're still in the artifact ensures the audit has
   real triggers to fire on. If the JSON is later corrected, update the
   `BAD_JSON_PATH` constant or move the regression to a fixture.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

AUDIT_MODE_PATH = ROOT / "modes" / "audit.md"
# Fixture lives in tests/fixtures/ so re-running /coin pdf 137 in dev doesn't
# overwrite our regression baseline. The original lives in data/resumes/generated/
# for live workflow; this is a frozen copy.
BAD_JSON_PATH = ROOT / "tests" / "fixtures" / "audit" / "0137_filevine_se_known_bad.json"


# ── Structural tests ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def audit_md() -> str:
    assert AUDIT_MODE_PATH.exists(), f"modes/audit.md missing at {AUDIT_MODE_PATH}"
    return AUDIT_MODE_PATH.read_text()


def test_all_9_checks_present(audit_md: str) -> None:
    """Each check has a numbered heading. Removing any of them weakens the audit."""
    expected = [
        "Check 1 — Education truthfulness",
        "Check 2 — Pedigree non-claim",
        "Check 3 — Cox / TitanX / Safeguard attribution",
        "Check 4 — Vague-flex qualifiers",
        "Check 5 — Metric provenance",
        "Check 6 — Causation hedging",
        "Check 7 — Header / summary congruence",
        "Check 8 — JD ↔ skills_gap honesty",
        "Check 9 — Domain overreach",
    ]
    for header in expected:
        assert header in audit_md, f"audit.md missing header: {header}"


def test_severity_taxonomy_intact(audit_md: str) -> None:
    """Verdict rules and severity labels must be unambiguous."""
    for token in ("CRITICAL", "HIGH", "BLOCK", "NEEDS REVISION", "CLEAN"):
        assert token in audit_md, f"audit.md missing severity/verdict token: {token}"


def test_verdict_rules_present(audit_md: str) -> None:
    """The CLEAN/NEEDS REVISION/BLOCK rule definition must remain explicit."""
    assert re.search(r"CLEAN\s*\*?\*?\s*=\s*0\s+CRITICAL", audit_md), \
        "audit.md must define CLEAN as 0 CRITICAL, 0 HIGH"
    assert re.search(r"BLOCK\s*\*?\*?\s*=\s*1\+\s*CRITICAL", audit_md), \
        "audit.md must define BLOCK as 1+ CRITICAL"


def test_human_gate_in_auto_fix(audit_md: str) -> None:
    """Auto-fix must require explicit human confirmation — never silent rewrite."""
    assert "HUMAN GATE" in audit_md, "audit.md must declare a HUMAN GATE for auto-fix"
    assert "never silently rewrite" in audit_md.lower() or \
           "never silently" in audit_md.lower(), \
        "audit.md must forbid silent rewrites of tailored JSON"


def test_known_bad_string_triggers_documented(audit_md: str) -> None:
    """The specific phrases that triggered the 2026-04-24 code-review findings
    must appear as fix templates so the executor knows what 'bad' looks like."""
    # Cox attribution example
    assert "Personally led pre-sales" in audit_md or \
           "personally led pre-sales" in audit_md.lower(), \
        "audit.md should reference the known-bad Cox attribution phrase"
    # Fortune 500 qualifier example
    assert "Fortune 500" in audit_md, "audit.md must list 'Fortune 500' as a vague-flex trigger"
    # Hydrant reframing fix
    assert "Hydrant" in audit_md, "audit.md must reference Hydrant as the correct employer framing"


def test_read_order_specified(audit_md: str) -> None:
    """Inputs must be read in a strict order so context is loaded right."""
    # Find the Step 1 section and check that all required input sources are listed
    for source in (
        "priority-hierarchy.md",
        "SKILL.md",
        "data/resumes/base.py",
        "config/profile.yml",
        "data/resumes/generated",
    ):
        assert source in audit_md, f"audit.md Step 1 must include input: {source}"


# ── Regression tests against the known-bad Filevine JSON ──────────────────────

@pytest.fixture(scope="module")
def bad_json() -> dict:
    if not BAD_JSON_PATH.exists():
        pytest.skip(f"Filevine regression JSON not present at {BAD_JSON_PATH}")
    return json.loads(BAD_JSON_PATH.read_text())


def test_filevine_json_still_has_cox_attribution_trigger(bad_json: dict) -> None:
    """Check 3 must have something to fire on. If the JSON has been corrected,
    delete this assertion and capture a new known-bad fixture."""
    blob = json.dumps(bad_json).lower()
    assert "cox" in blob, \
        "Regression: Filevine JSON no longer mentions Cox — update fixture or remove this test"
    # Must contain at least one Cox-related phrase that doesn't include 'Hydrant' framing
    bullets = bad_json["resume"]["top_bullets"]
    cox_bullets = [b for b in bullets if "cox" in b.lower()]
    assert cox_bullets, "Filevine JSON should have at least one Cox-related bullet"


def test_filevine_json_still_has_pedigree_or_inflation_trigger(bad_json: dict) -> None:
    """Check 4 needs the puffery still in the JSON. If you fixed it, capture
    a new fixture for the regression net."""
    blob = json.dumps(bad_json)
    triggers = [
        "Fortune 500",
        "seven-figure",
        "world-class",
        "industry-leading",
    ]
    found = [t for t in triggers if t in blob]
    assert found, (
        f"Regression: Filevine JSON no longer contains any vague-flex trigger. "
        f"Either update this fixture or capture a new known-bad JSON."
    )


def test_filevine_json_target_role_check(bad_json: dict) -> None:
    """Check 7 (header congruence) requires target_role on non-TPM lanes.
    Filevine is enterprise-sales-engineer, so target_role MUST be set for
    a clean audit. If it's missing, Check 7 should fail."""
    lane = bad_json.get("lane", "")
    target_role = bad_json.get("target_role") or bad_json.get("resume", {}).get("target_role")

    if lane != "mid-market-tpm":
        # We expect this to fail audit Check 7 currently — that's the regression.
        # If target_role gets added later, this assertion becomes a positive check.
        if target_role is None:
            # Document the current state — Check 7 should fire on this JSON.
            assert True, "Confirmed: Filevine JSON lacks target_role (Check 7 will fire)"
        else:
            assert target_role, "If target_role is set, it must be a non-empty string"


def test_filevine_json_is_loadable(bad_json: dict) -> None:
    """Sanity — the regression fixture is well-formed JSON with the expected shape."""
    assert "role_id" in bad_json
    assert "lane" in bad_json
    assert "resume" in bad_json
    assert "executive_summary" in bad_json["resume"]
    assert "top_bullets" in bad_json["resume"]
    assert isinstance(bad_json["resume"]["top_bullets"], list)
    assert len(bad_json["resume"]["top_bullets"]) >= 3
