"""PDF parser — clean-room 4-step heuristic. Tests against a RenderCV-rendered PDF."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── Fixture: render a known-good PDF once per session ──────────────────

@pytest.fixture(scope="session")
def sample_pdf_path(tmp_path_factory) -> Path:
    """Generate a RenderCV sample PDF for parser tests to consume."""
    from rendercv.schema.sample_generator import create_sample_rendercv_pydantic_model
    from rendercv.renderer.typst import generate_typst
    from rendercv.renderer.pdf_png import generate_pdf

    tmpdir = tmp_path_factory.mktemp("parser_sample")
    m = create_sample_rendercv_pydantic_model(theme="engineeringresumes")
    m.settings.render_command.output_folder = tmpdir
    m.settings.render_command.typst_path = tmpdir / "cv.typ"
    m.settings.render_command.pdf_path = tmpdir / "cv.pdf"
    typst_path = generate_typst(m)
    pdf_path = generate_pdf(m, typst_path)
    return Path(pdf_path)


@pytest.fixture(scope="session")
def sean_pdf_path(tmp_path_factory) -> Path:
    """Render Sean's resume via the adapter; this exercises the actual coin path."""
    from data.resumes.base import PROFILE
    from careerops.rendercv_adapter import coin_to_rendercv_model
    from rendercv.renderer.typst import generate_typst
    from rendercv.renderer.pdf_png import generate_pdf

    tmpdir = tmp_path_factory.mktemp("sean_sample")
    gen = dict(PROFILE)
    gen["archetype_id"] = "mid-market-tpm"
    gen["executive_summary"] = (
        "Senior Technical Program Manager with 15+ years orchestrating wireless and IoT programs."
    )
    gen["top_bullets"] = [
        "Drove Cox program to $1M Y1 revenue 12 months ahead of schedule.",
    ]

    m = coin_to_rendercv_model(
        gen, theme="engineeringresumes", output_dir=tmpdir, output_basename="sean",
    )
    typst_path = generate_typst(m)
    pdf_path = generate_pdf(m, typst_path)
    return Path(pdf_path)


# ── 4 steps + ATS score ────────────────────────────────────────────────

def test_extract_text_items_returns_lines(sample_pdf_path):
    from careerops.parser import extract_text_items
    items, n_pages = extract_text_items(sample_pdf_path)
    assert n_pages >= 1
    assert len(items) >= 20
    assert all(it.text.strip() for it in items)


def test_group_items_into_lines_preserves_reading_order(sample_pdf_path):
    from careerops.parser import extract_text_items, group_items_into_lines
    items, _ = extract_text_items(sample_pdf_path)
    lines = group_items_into_lines(items)
    # Lines on page 0 must come before lines on page 1.
    page_idxs = [ln.items[0].page_idx for ln in lines if ln.items]
    assert page_idxs == sorted(page_idxs), "lines must be page-major reading order"


def test_detect_sections_on_rendercv_sample(sample_pdf_path):
    from careerops.parser import parse_resume_pdf
    res = parse_resume_pdf(sample_pdf_path)
    canonicals = {s.canonical for s in res.sections}
    # RenderCV's sample includes Education + Experience + Skills minimum.
    assert "education" in canonicals
    assert "experience" in canonicals
    assert "skills" in canonicals


def test_extract_fields_finds_email(sample_pdf_path):
    from careerops.parser import parse_resume_pdf
    res = parse_resume_pdf(sample_pdf_path)
    assert "email" in res.fields
    assert "@" in res.fields["email"].value


def test_extract_fields_finds_name_on_sean_pdf(sean_pdf_path):
    from careerops.parser import parse_resume_pdf
    res = parse_resume_pdf(sean_pdf_path)
    assert "name" in res.fields
    assert "Sean" in res.fields["name"].value


def test_ats_score_ge_85_on_sean_pdf(sean_pdf_path):
    """Sean's RenderCV-rendered resume must score ≥85 on the parser self-check."""
    from careerops.parser import parse_resume_pdf
    res = parse_resume_pdf(sean_pdf_path)
    score = res.ats_score()
    assert score >= 85, f"Sean's PDF scored only {score}/100"


def test_ats_score_components(sean_pdf_path):
    from careerops.parser import parse_resume_pdf
    res = parse_resume_pdf(sean_pdf_path)
    # Verify the canonical signals.
    assert "name" in res.fields
    assert "email" in res.fields
    assert "phone" in res.fields  # Sean's PDF has phone
    canonicals = {s.canonical for s in res.sections}
    assert {"experience", "education", "skills"}.issubset(canonicals)


def test_section_canonicals_match_known_labels():
    from careerops.parser import _classify_section_header, TextLine

    def _line(text, height=14):
        return TextLine(items=[], y=0, text=text, avg_height=height)

    body_h = 10.0
    assert _classify_section_header(_line("EXPERIENCE"), body_h) == "experience"
    assert _classify_section_header(_line("Education"), body_h) == "education"
    assert _classify_section_header(_line("Technical Skills"), body_h) == "skills"
    assert _classify_section_header(_line("Random Body Text"), body_h) is None


def test_no_unicode_glyph_garbage_predicate():
    from careerops.parser import _no_unicode_glyph_garbage
    assert _no_unicode_glyph_garbage("Plain text resume content")
    assert not _no_unicode_glyph_garbage("Has  PUA char")  # FontAwesome PUA range


def test_dated_lines_predicate():
    from careerops.parser import _at_least_n_dated_lines, TextLine

    def _line(text):
        return TextLine(items=[], y=0, text=text, avg_height=10)

    lines = [
        _line("Cox · Jan 2020 – Dec 2024"),
        _line("Hydrant · Jul 2019 – Dec 2024"),
        _line("Utah Broadband · Apr 2013 – Jul 2019"),
    ]
    assert _at_least_n_dated_lines(lines, n=3)
