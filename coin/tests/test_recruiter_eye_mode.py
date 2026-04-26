"""recruiter-eye.md — mode-structure regression tests."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECRUITER_MD = (ROOT / "modes" / "recruiter-eye.md").read_text()


def test_mode_file_exists():
    assert (ROOT / "modes" / "recruiter-eye.md").exists()


def test_loads_shared_md_first():
    assert "Load `modes/_shared.md` first" in RECRUITER_MD


def test_eight_visual_checks_present():
    for label in (
        "### 2.1 Name presence",
        "### 2.2 Contact block",
        "### 2.3 Date format",
        "### 2.4 Section labels",
        "### 2.5 Bullet density",
        "### 2.6 Unicode glyph",
        "### 2.7 Page count",
        "### 2.8 Mono-column",
    ):
        assert label in RECRUITER_MD, f"missing visual check: {label}"


def test_page_count_strict_for_ats_variant():
    assert "ATS-strict" in RECRUITER_MD
    assert "n_pages > 1" in RECRUITER_MD
    assert "n_pages > 2" in RECRUITER_MD


def test_glyph_blacklist_includes_pua_range():
    assert "U+E000" in RECRUITER_MD
    assert "U+F8FF" in RECRUITER_MD
    assert "Private-Use-Area" in RECRUITER_MD or "PUA" in RECRUITER_MD


def test_aggregate_verdict_binary():
    """The aggregate must be a binary PASS/FAIL — no middle ground."""
    assert "PASS = no FAILs" in RECRUITER_MD
    assert "FAIL = any FAIL" in RECRUITER_MD


def test_persists_to_render_artifact_notes():
    assert "render_artifact" in RECRUITER_MD
    assert "notes" in RECRUITER_MD


def test_hard_refusals_present():
    assert "## Hard refusals" in RECRUITER_MD
    refusals_section = RECRUITER_MD.split("## Hard refusals")[1].split("##")[0]
    assert refusals_section.count("|") >= 8  # at least 4 refusal rows (2 cells each)


def test_uses_clean_room_parser():
    assert "careerops.parser" in RECRUITER_MD
    assert "parse_resume_pdf" in RECRUITER_MD
