"""JD parser — deterministic skill extraction + must_have/nice_to_have classification."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops.jd_parser import (
    extract_skills_from_jd,
    build_jd_signals_prompt,
    JdSignalsPromptInputs,
    validate_jd_signals_response,
    persist_jd_signals,
    JD_SIGNAL_SCHEMA,
)


def _all_skills(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM skill").fetchall()]
    conn.close()
    return rows


SAMPLE_JD = """
Senior Technical Program Manager - IoT Platform

Required:
- 10+ years technical program management experience
- Strong RF / wireless / IoT background
- Experience with B2B SaaS platforms

Nice to have:
- Salesforce CRM experience
- Aerospace industry exposure

Compensation: $180,000 - $230,000 base.
"""


def test_extract_skills_classifies_required_section(tmp_path):
    from scripts.migrations import m006_seed_lightcast as m006
    db = tmp_path / "t.db"
    m006.apply(db)
    skills = _all_skills(db)

    hits = extract_skills_from_jd(SAMPLE_JD, all_skills=skills)
    must_have = [h for h in hits if h.term_kind == "must_have"]
    nice_to_have = [h for h in hits if h.term_kind == "nice_to_have"]

    must_have_terms = {h.term for h in must_have}
    nice_terms = {h.term for h in nice_to_have}

    assert any("Program Management" in t for t in must_have_terms)
    assert any("B2B SaaS" in t for t in must_have_terms)
    assert "Salesforce" in nice_terms


def test_extract_skills_no_hits_on_unrelated_jd(tmp_path):
    from scripts.migrations import m006_seed_lightcast as m006
    db = tmp_path / "t.db"
    m006.apply(db)
    skills = _all_skills(db)

    hits = extract_skills_from_jd("We are hiring a barista. Coffee skills required.", all_skills=skills)
    assert hits == []


def test_signal_prompt_contains_jd_text():
    prompt = build_jd_signals_prompt(JdSignalsPromptInputs(jd_text=SAMPLE_JD))
    assert "JOB DESCRIPTION" in prompt
    assert "Senior Technical Program Manager" in prompt
    assert "JSON SCHEMA" in prompt


def test_validate_signals_response_accepts_valid():
    response = json.dumps({
        "seniority_cap": "Senior",
        "comp_band": {"low": 180000, "high": 230000, "currency": "USD", "explicit_in_jd": True},
        "industry_keywords": ["IoT", "B2B SaaS"],
        "role_verbs": ["orchestrate", "deliver", "lead"],
        "remote_friendly": None,
        "company_stage": None,
    })
    res = validate_jd_signals_response(response)
    assert res.valid


def test_validate_signals_rejects_missing_required():
    response = json.dumps({"seniority_cap": "Senior"})
    res = validate_jd_signals_response(response)
    assert not res.valid


def test_persist_jd_signals_writes_keywords(tmp_path):
    from scripts.migrations import m005_experience_db as m005
    from scripts.migrations import m006_seed_lightcast as m006
    from careerops import experience as exp

    db = tmp_path / "t.db"
    m005.apply(db)
    m006.apply(db)
    skills = _all_skills(db)

    # roles table needed for FK semantics — create minimal stub.
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE roles (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT)")
    conn.execute("INSERT INTO roles (id, url) VALUES (42, 'https://test')")
    conn.commit()
    conn.close()

    hits = extract_skills_from_jd(SAMPLE_JD, all_skills=skills)
    n = persist_jd_signals(
        role_id=42, skill_hits=hits,
        signals={
            "seniority_cap": "Senior",
            "industry_keywords": ["IoT"],
        },
        db_path=db,
    )
    assert n > 0
    rows = exp.list_jd_keywords(42, db_path=db)
    terms = [r["term"] for r in rows]
    assert "seniority:Senior" in terms
    assert "IoT" in terms


def test_jd_signal_schema_structure():
    assert JD_SIGNAL_SCHEMA["type"] == "object"
    for f in ("seniority_cap", "comp_band", "industry_keywords", "role_verbs"):
        assert f in JD_SIGNAL_SCHEMA["required"]
