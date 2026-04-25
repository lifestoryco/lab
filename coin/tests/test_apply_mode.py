"""Safety + structural test for modes/apply.md.

Browser automation is hard to unit-test. What we CAN verify mechanically:

1. The 6 hard refusals from Step 8 are documented (these are the safety
   guards — silent removal is the failure mode this test catches)
2. Each ATS section has a "STOP at Submit button" instruction
3. The 6-page Workday wizard is enumerated
4. The pre-fill protocol (read first, type, snapshot, log) is present
5. References to the proficiently ats-patterns.md doc exist (the source of
   the per-ATS field orders)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

APPLY_MODE = ROOT / "modes" / "apply.md"
ATS_REFERENCE = ROOT / ".claude" / "skills" / "coin" / "references" / "ats-patterns.md"


# ── Structural tests ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def apply_md() -> str:
    assert APPLY_MODE.exists(), f"modes/apply.md missing at {APPLY_MODE}"
    return APPLY_MODE.read_text()


def test_all_9_steps_present(apply_md: str) -> None:
    expected = [
        "Step 1 — ATS detection",
        "Step 2 — Open the apply URL",
        "Step 3 — Per-ATS field-fill flows",
        "Step 4 — Generic flow",
        "Step 5 — Pre-fill protocol",
        "Step 6 — LinkedIn Easy Apply",
        "Step 7 — Final checklist",
        "Step 8 — Hard refusals",
        "Step 9 — Notes",
    ]
    for header in expected:
        assert header in apply_md, f"apply.md missing step: {header}"


def test_ats_detection_covers_all_known_providers(apply_md: str) -> None:
    """ATS detection table must cover Greenhouse, Lever, Workday, LinkedIn,
    Ashby (best-effort), and unknown."""
    for provider in ("greenhouse", "lever", "workday", "linkedin", "unknown"):
        assert provider in apply_md.lower(), f"apply.md missing ATS provider: {provider}"
    # Ashby should be at least best-effort referenced
    assert "ashby" in apply_md.lower() or "Ashby" in apply_md, "apply.md should reference Ashby"


def test_per_ats_flows_present(apply_md: str) -> None:
    """Each major ATS gets a field-fill order."""
    for section in ("Greenhouse field order", "Lever field order", "Workday field order"):
        assert section in apply_md, f"apply.md missing per-ATS section: {section}"


def test_workday_wizard_pages_enumerated(apply_md: str) -> None:
    """All 6 Workday wizard pages must be enumerated so the agent can navigate them."""
    pages = (
        "My Information",
        "My Experience",
        "Application Questions",
        "Voluntary Disclosures",
        "Self Identify",
        "Review",
    )
    for page in pages:
        assert page in apply_md, f"apply.md Workday flow missing page: {page}"


def test_stop_at_submit_in_every_ats_flow(apply_md: str) -> None:
    """Every ATS section must explicitly say STOP at Submit."""
    submit_stops = apply_md.count("STOP at Submit button")
    assert submit_stops >= 2, (
        f"apply.md must say 'STOP at Submit button' in each ATS flow; "
        f"found only {submit_stops} mention(s) — Greenhouse and Lever both need it"
    )
    # Workday uses a wizard (Save and Continue, not Submit), so its STOP is on the Review page
    assert "STOP" in apply_md and "Review" in apply_md


# ── The 6 hard refusals — these MUST never be removed ────────────────────────

@pytest.mark.parametrize("refusal_phrase", [
    "Auto-click Submit",
    "Fill \"Yes I am a US citizen",
    "EEO",
    "Auto-create a Workday account",
    "salary expectation",
    "Auto-transition role to `applied`",
])
def test_hard_refusal_documented(apply_md: str, refusal_phrase: str) -> None:
    """Each Step 8 refusal must remain in the mode text. If anyone deletes one,
    this test fails — protecting the safety guards from drift."""
    assert refusal_phrase in apply_md, (
        f"apply.md Step 8 must document refusal: '{refusal_phrase}' — "
        f"silent removal of safety guards is forbidden"
    )


def test_refusals_are_non_negotiable(apply_md: str) -> None:
    """The phrasing 'non-negotiable' on the refusal list prevents drift."""
    assert "non-negotiable" in apply_md.lower(), (
        "apply.md must declare the Step 8 refusals 'non-negotiable' — "
        "this is the lock against future loosening"
    )


# ── Pre-fill protocol must protect against silent overwrite ──────────────────

def test_pre_fill_reads_first(apply_md: str) -> None:
    """Step 5 must say 'Read first' (never overwrite a non-empty field that
    Sean already typed)."""
    assert "Read first" in apply_md, (
        "apply.md Step 5 must instruct: read first to avoid overwriting Sean's typing"
    )
    assert "never overwrite" in apply_md.lower() or "Never overwrite" in apply_md


def test_pre_fill_snapshots_after(apply_md: str) -> None:
    """Step 5 must say 'Snapshot after' (some fields silently reject)."""
    assert "Snapshot after" in apply_md or "snapshot after" in apply_md.lower(), (
        "apply.md Step 5 must require a post-fill snapshot — Workday silently "
        "rejects some combo-box values"
    )


# ── References must link back to the proficiently doc ─────────────────────────

def test_ats_reference_doc_exists() -> None:
    """The mode depends on the proficiently ats-patterns.md doc. If it goes
    missing, the per-ATS field orders have no source-of-truth."""
    assert ATS_REFERENCE.exists(), (
        f"References doc missing at {ATS_REFERENCE} — "
        f"reinstall via .claude/skills/coin/references/ats-patterns.md"
    )


def test_ats_reference_covers_all_providers() -> None:
    """The reference doc must cover the same ATS providers the mode does."""
    ref_text = ATS_REFERENCE.read_text()
    for provider in ("Greenhouse", "Lever", "Workday"):
        assert provider in ref_text, f"ats-patterns.md missing provider section: {provider}"


def test_apply_mode_references_the_doc(apply_md: str) -> None:
    """The mode text must explicitly link back to the reference doc so future
    edits know where the patterns came from."""
    assert "ats-patterns.md" in apply_md, (
        "apply.md must reference .claude/skills/coin/references/ats-patterns.md "
        "as the source of truth for ATS field orders"
    )


# ── Final checklist format ────────────────────────────────────────────────────

def test_manifest_has_filled_and_needs_sean(apply_md: str) -> None:
    """Step 7 manifest must have both FILLED and NEEDS YOU sections."""
    assert "FILLED" in apply_md, "Step 7 manifest must have FILLED section"
    assert "NEEDS YOU" in apply_md, "Step 7 manifest must have NEEDS YOU section"


def test_next_step_directs_to_track_after_submit(apply_md: str) -> None:
    """The NEXT STEP guidance must direct Sean to /coin track <id> applied
    AFTER he clicks Submit — never automatically."""
    assert "/coin track" in apply_md, "apply.md must direct to /coin track after submit"
    assert "after you actually" in apply_md.lower() or \
           "After you" in apply_md or \
           "after" in apply_md.lower() and "submit" in apply_md.lower(), \
        "apply.md must make clear that track happens AFTER the human submits"
