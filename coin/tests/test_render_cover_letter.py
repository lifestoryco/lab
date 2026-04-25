"""Smoke test for scripts/render_cover_letter.py.

Builds a fixture cover JSON, renders to a temp file, asserts:
  - PDF file created and > 4KB
  - Renderer refuses if audit_passes is false
  - Renderer rejects missing required keys
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _fixture_doc(audit_passes: bool = True) -> dict:
    return {
        "role_id": 9999,
        "company": "Filevine",
        "title": "Senior Solutions Engineer",
        "lane": "enterprise-sales-engineer",
        "recipient_name": None,
        "today": "2026-04-25",
        "paragraphs": {
            "hook": (
                "Filevine is scaling enterprise legal SaaS. That is the problem I "
                "solved at Hydrant — Cox True Local Labs hit $1M Year 1 revenue "
                "twelve months ahead of schedule under my program ownership."
            ),
            "proof": (
                "At Utah Broadband (Enterprise AM, 2013-2019), I grew ARR from $6M "
                "to $13M and led the technical pre-sales motion that drove the $27M "
                "acquisition by Boston Omaha. As Hydrant's fractional COO at TitanX, "
                "I shaped the operational cadence that closed a $27M Series A in "
                "under two years. Both pull on the same muscle the Filevine JD "
                "names: enterprise-grade discovery, demo, and post-sales delivery."
            ),
            "fit": (
                "I'm Salt Lake City based and hire-ready for the Lehi / Draper "
                "footprint. I don't have a CS degree; I close that gap with PMP "
                "rigor and 15 years of wireless / IoT delivery."
            ),
        },
        "stories_used": ["utah_broadband_acquisition", "cox_true_local_labs"],
        "jd_keywords_cited": ["enterprise SaaS", "pre-sales", "discovery"],
        "word_count": 162,
        "audit_passes": audit_passes,
        "generated_at": "2026-04-25T10:00:00",
    }


def test_render_smoke(tmp_path):
    from scripts.render_cover_letter import render

    json_path = tmp_path / "0009_test_cover.json"
    json_path.write_text(json.dumps(_fixture_doc(audit_passes=True)))
    out_path = tmp_path / "0009_test_cover.pdf"

    render(json_path, out_path)
    assert out_path.exists()
    assert out_path.stat().st_size > 4 * 1024


def test_render_refuses_unaudited(tmp_path):
    from scripts.render_cover_letter import render

    json_path = tmp_path / "0009_unaudited.json"
    json_path.write_text(json.dumps(_fixture_doc(audit_passes=False)))
    with pytest.raises(ValueError, match="audit_passes"):
        render(json_path, tmp_path / "x.pdf")


def test_render_rejects_missing_keys(tmp_path):
    from scripts.render_cover_letter import render

    bad = {"company": "X"}
    json_path = tmp_path / "bad.json"
    json_path.write_text(json.dumps(bad))
    with pytest.raises(ValueError, match="missing keys"):
        render(json_path, tmp_path / "x.pdf")


def test_render_rejects_empty_paragraph(tmp_path):
    from scripts.render_cover_letter import render

    doc = _fixture_doc()
    doc["paragraphs"]["fit"] = ""
    json_path = tmp_path / "empty.json"
    json_path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match="paragraphs.fit"):
        render(json_path, tmp_path / "x.pdf")
