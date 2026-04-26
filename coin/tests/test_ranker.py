"""Ranker — JSON schema contract + deterministic response validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops.ranker import (
    RANKER_SCHEMA,
    RankerPromptInputs,
    build_ranker_prompt,
    validate_ranker_response,
)


def test_schema_required_fields():
    assert RANKER_SCHEMA["type"] == "object"
    for f in ("jd_signals", "bullet_scores", "top_k_per_role"):
        assert f in RANKER_SCHEMA["required"]


def test_build_prompt_contains_jd_and_payload():
    payload = [
        {"accomplishment": {"id": 1, "title": "Cox $1M Y1"}, "outcomes": [], "evidence": [], "skills": [], "lane_relevance": 100},
        {"accomplishment": {"id": 2, "title": "TitanX $27M Series A"}, "outcomes": [], "evidence": [], "skills": [], "lane_relevance": 90},
    ]
    prompt = build_ranker_prompt(RankerPromptInputs(
        lane_slug="mid-market-tpm",
        payload=payload,
        jd_text="Senior TPM - IoT Platform.",
        jd_role_id=42,
        k=5,
    ))
    assert "Senior TPM - IoT Platform." in prompt
    assert "JSON SCHEMA" in prompt
    assert "mid-market-tpm" in prompt
    # payload accomplishment_ids serialized:
    assert "Cox $1M Y1" in prompt or "$1M" in prompt
    # K explicit:
    assert "K: 5" in prompt


def test_validate_accepts_clean_response():
    response = json.dumps({
        "jd_signals": {
            "must_have_skills": ["program management"],
            "nice_to_have": [],
        },
        "bullet_scores": [
            {"accomplishment_id": 1, "score": 0.9, "rationale": "fits"},
            {"accomplishment_id": 2, "score": 0.7, "rationale": "adjacent"},
        ],
        "top_k_per_role": [1, 2],
    })
    res = validate_ranker_response(
        response, expected_accomplishment_ids={1, 2}, k=2,
    )
    assert res.valid, res.errors
    assert res.top_k == [1, 2]


def test_validate_rejects_hallucinated_accomplishment_id():
    response = json.dumps({
        "jd_signals": {"must_have_skills": [], "nice_to_have": []},
        "bullet_scores": [
            {"accomplishment_id": 999, "score": 0.9, "rationale": ""},
        ],
        "top_k_per_role": [999],
    })
    res = validate_ranker_response(
        response, expected_accomplishment_ids={1, 2},
    )
    assert not res.valid
    assert any("hallucinated" in e for e in res.errors)


def test_validate_rejects_score_out_of_bounds():
    response = json.dumps({
        "jd_signals": {"must_have_skills": [], "nice_to_have": []},
        "bullet_scores": [
            {"accomplishment_id": 1, "score": 1.5, "rationale": ""},
        ],
        "top_k_per_role": [1],
    })
    res = validate_ranker_response(
        response, expected_accomplishment_ids={1},
    )
    assert not res.valid


def test_validate_rejects_top_k_length_mismatch():
    response = json.dumps({
        "jd_signals": {"must_have_skills": [], "nice_to_have": []},
        "bullet_scores": [
            {"accomplishment_id": 1, "score": 0.9, "rationale": ""},
            {"accomplishment_id": 2, "score": 0.7, "rationale": ""},
        ],
        "top_k_per_role": [1, 2],
    })
    res = validate_ranker_response(response, expected_accomplishment_ids={1, 2}, k=5)
    assert not res.valid
    assert any("length" in e for e in res.errors)


def test_validate_rejects_malformed_json():
    res = validate_ranker_response("not valid json")
    assert not res.valid
    assert any("JSON decode" in e for e in res.errors)
