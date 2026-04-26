"""RenderCV adapter — Coin generated_json → RenderCVModel mapping."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def coin_resume_json():
    """Realistic Coin generated_json shape from base.py."""
    from data.resumes.base import PROFILE
    gen = dict(PROFILE)
    gen.update({
        "archetype_id": "mid-market-tpm",
        "role_id": 4,
        "executive_summary": "Senior TPM orchestrating wireless and IoT programs.",
        "top_bullets": [
            "Drove Cox program to $1M Y1 revenue.",
            "Operationalized TitanX to $27M Series A.",
        ],
    })
    return gen


def test_coin_to_rendercv_dict_emits_required_sections(coin_resume_json):
    from careerops.rendercv_adapter import coin_to_rendercv_dict
    d = coin_to_rendercv_dict(coin_resume_json, theme="engineeringresumes")
    assert "cv" in d
    assert "design" in d
    sections = d["cv"]["sections"]
    assert "Summary" in sections
    assert "Selected Achievements" in sections
    assert "Experience" in sections
    assert "Skills" in sections
    assert "Education" in sections


def test_coin_to_rendercv_dict_credentials_appended_to_name(coin_resume_json):
    from careerops.rendercv_adapter import coin_to_rendercv_dict
    d = coin_to_rendercv_dict(coin_resume_json, theme="classic")
    assert "Sean Ivins, PMP, MBA" in d["cv"]["name"]


def test_phone_normalizer():
    from careerops.rendercv_adapter import _normalize_phone
    assert _normalize_phone("801.803.3084") == "+1 801 803 3084"
    assert _normalize_phone("(801) 803-3084") == "+1 801 803 3084"
    assert _normalize_phone("801-803-3084") == "+1 801 803 3084"
    assert _normalize_phone("18018033084") == "+1 801 803 3084"
    assert _normalize_phone(None) is None
    assert _normalize_phone("") is None


def test_iso_month_normalizer():
    from careerops.rendercv_adapter import _to_iso_month
    assert _to_iso_month("Jan 2025") == "2025-01"
    assert _to_iso_month("Apr 2013") == "2013-04"
    assert _to_iso_month("Present") == "present"
    assert _to_iso_month("present") == "present"
    assert _to_iso_month("2024") == "2024"
    assert _to_iso_month(None) is None


def test_themes_for_lane_returns_primary_and_alts():
    from careerops.rendercv_adapter import themes_for_lane
    t = themes_for_lane("mid-market-tpm")
    assert t["primary"] == "engineeringresumes"
    assert "classic" in t["alts"]


def test_themes_for_lane_falls_back_for_unknown():
    from careerops.rendercv_adapter import themes_for_lane
    t = themes_for_lane("not-a-real-lane")
    assert "primary" in t


def test_coin_to_rendercv_model_builds(coin_resume_json, tmp_path):
    """End-to-end: dict → RenderCVModel."""
    from careerops.rendercv_adapter import coin_to_rendercv_model
    m = coin_to_rendercv_model(
        coin_resume_json, theme="engineeringresumes",
        output_dir=tmp_path, output_basename="t",
    )
    assert m.cv.name.startswith("Sean Ivins")
    section_names = list(m.cv.sections.keys())
    assert "Experience" in section_names
    assert "Skills" in section_names


def test_rendercv_model_overrides_output_paths(coin_resume_json, tmp_path):
    from careerops.rendercv_adapter import coin_to_rendercv_model
    m = coin_to_rendercv_model(
        coin_resume_json, theme="engineeringresumes",
        output_dir=tmp_path, output_basename="custom",
    )
    assert m.settings.render_command.pdf_path == tmp_path / "custom.pdf"
    assert m.settings.render_command.typst_path == tmp_path / "custom.typ"
    assert m.settings.render_command.dont_generate_html
    assert m.settings.render_command.dont_generate_png


def test_render_pdf_passes_parser_self_check(coin_resume_json, tmp_path):
    """Adapter → RenderCV → PDF → re-parse → ATS ≥85."""
    from careerops.rendercv_adapter import coin_to_rendercv_model
    from rendercv.renderer.typst import generate_typst
    from rendercv.renderer.pdf_png import generate_pdf
    from careerops.parser import parse_resume_pdf

    m = coin_to_rendercv_model(
        coin_resume_json, theme="engineeringresumes",
        output_dir=tmp_path, output_basename="t",
    )
    typst_path = generate_typst(m)
    pdf_path = generate_pdf(m, typst_path)
    res = parse_resume_pdf(pdf_path)
    assert res.ats_score() >= 85, f"got {res.ats_score()}/100"
