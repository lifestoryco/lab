"""Skill tagger — deterministic match + structured-output validation."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops.skill_tagger import (
    deterministic_skill_match,
    build_skill_tag_prompt,
    SkillTagPromptInputs,
    validate_skill_tag_response,
    SKILL_TAG_SCHEMA,
)


def _all_skills(db_path):
    """Helper: get all skill rows from a seeded test DB."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute("SELECT * FROM skill").fetchall()]
    conn.close()
    return rows


def test_deterministic_match_finds_program_management(tmp_path):
    from scripts.migrations import m006_seed_lightcast as m006
    db = tmp_path / "t.db"
    m006.apply(db)
    skills = _all_skills(db)

    matches = deterministic_skill_match(
        "Managed program execution for Cox Communications.",
        all_skills=skills,
    )
    assert any(m.skill_slug == "program-execution" for m in matches)


def test_deterministic_match_no_partial_substring():
    """Phrase 'iot' inside 'patriot' must NOT match."""
    skills = [{"slug": "iot", "name": "IoT", "category": "IoT"}]
    matches = deterministic_skill_match(
        "Patriotic engineering on patriot missile systems.",
        all_skills=skills,
    )
    # Must be empty because IoT is too short and would mis-match
    # 'patriot'/'patriotic' without word boundaries.
    assert all(m.skill_slug != "iot" for m in matches)


def test_build_prompt_contains_candidates(tmp_path):
    from scripts.migrations import m006_seed_lightcast as m006
    db = tmp_path / "t.db"
    m006.apply(db)
    skills = _all_skills(db)
    prompt = build_skill_tag_prompt(SkillTagPromptInputs(
        accomplishment_text="Drove Cox program to $1M revenue.",
        candidate_skills=skills[:5],
    ))
    assert "candidate_skills" in prompt
    assert "JSON SCHEMA" in prompt
    assert skills[0]["slug"] in prompt


def test_validate_rejects_hallucinated_slug():
    valid = {"technical-program-management", "cross-functional-orchestration"}
    response = json.dumps({
        "suggestions": [
            {"skill_slug": "technical-program-management", "weight": 9, "rationale": "ok"},
            {"skill_slug": "totally-fake", "weight": 5, "rationale": "hallucinated"},
        ]
    })
    res = validate_skill_tag_response(response, valid_slugs=valid)
    assert not res.valid
    assert any("hallucinated" in e for e in res.errors)
    # The valid one survives:
    assert len(res.suggestions) == 1
    assert res.suggestions[0]["skill_slug"] == "technical-program-management"


def test_validate_rejects_out_of_bounds_weight():
    valid = {"x"}
    response = json.dumps({
        "suggestions": [{"skill_slug": "x", "weight": 99, "rationale": ""}],
    })
    res = validate_skill_tag_response(response, valid_slugs=valid)
    assert not res.valid


def test_validate_accepts_clean_response():
    valid = {"a", "b"}
    response = json.dumps({
        "suggestions": [
            {"skill_slug": "a", "weight": 8, "rationale": "fits"},
            {"skill_slug": "b", "weight": 5, "rationale": "adjacent"},
        ],
    })
    res = validate_skill_tag_response(response, valid_slugs=valid)
    assert res.valid
    assert len(res.suggestions) == 2


def test_schema_required_fields():
    assert SKILL_TAG_SCHEMA["type"] == "object"
    assert "suggestions" in SKILL_TAG_SCHEMA["required"]
