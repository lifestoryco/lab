"""Bullet ranker — JSON schema + helpers for the structured-output prompt
consumed by modes/tailor.md Step 2.

Per founder decision: at 12 accomplishments × 4 lanes, Claude IS the
ranker (not a FastEmbed cosine-similarity model). Determinism comes from
temperature=0 + structured-output JSON schema + accomplishment_id
tie-break ordering.

Usage from modes/tailor.md:
  1. Load assemble_for_lane(lane_slug, ...) into a dict.
  2. Construct ranker prompt via build_ranker_prompt(payload, jd_text).
  3. Have Claude (host session) emit JSON conforming to RANKER_SCHEMA.
  4. Validate response via validate_ranker_response().
  5. Pass top-K to the rewrite step.

This module does NOT call any LLM. It defines the contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


# ── JSON schema for the ranker prompt's response ────────────────────────

RANKER_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CoinRankerResponse",
    "type": "object",
    "required": ["jd_signals", "bullet_scores", "top_k_per_role"],
    "additionalProperties": False,
    "properties": {
        "jd_signals": {
            "type": "object",
            "required": ["must_have_skills", "nice_to_have"],
            "additionalProperties": False,
            "properties": {
                "must_have_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills/keywords explicitly required in the JD",
                },
                "nice_to_have": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "seniority_cap": {
                    "type": ["string", "null"],
                    "description": "Highest title-level the JD targets, e.g. 'Senior', 'Staff', 'Principal'",
                },
                "comp_band": {
                    "type": ["object", "null"],
                    "properties": {
                        "low": {"type": ["number", "null"]},
                        "high": {"type": ["number", "null"]},
                    },
                    "additionalProperties": False,
                },
                "recency_window_years": {
                    "type": ["integer", "null"],
                    "description": "Roles older than this are weighted down",
                },
                "industry_keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        "bullet_scores": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["accomplishment_id", "score", "rationale"],
                "additionalProperties": False,
                "properties": {
                    "accomplishment_id": {"type": "integer"},
                    "score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "rationale": {"type": "string"},
                    "matches_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "seniority_alignment": {
                        "type": ["string", "null"],
                        "description": "'fit' | 'stretch' | 'overshoot'",
                    },
                },
            },
        },
        "top_k_per_role": {
            "type": "array",
            "description": "Final K winners, ordered best-first. accomplishment_id must appear in bullet_scores.",
            "items": {"type": "integer"},
        },
    },
}


# ── Prompt construction helper ──────────────────────────────────────────

@dataclass
class RankerPromptInputs:
    lane_slug: str
    payload: list[dict[str, Any]]    # output of experience.assemble_for_lane()
    jd_text: str                     # raw JD body
    jd_role_id: int | None = None
    k: int = 6                       # number of top winners to ask for
    seniority_constraint: str | None = None  # higher-context guidance


def build_ranker_prompt(inputs: RankerPromptInputs) -> str:
    """Render the prompt body. modes/tailor.md prepends Claude-Code system framing."""
    lines = [
        "You are coin's bullet-ranker. Score each accomplishment for fit "
        "against the job description. Then pick the top-K winners.",
        "",
        "RULES:",
        "1. Score each accomplishment 0.0..1.0 based on relevance to JD must-haves + nice-to-haves.",
        "2. The score MUST reflect skills + outcomes + seniority alignment, not prose quality.",
        "3. Only consider the structured fact rows (accomplishment, outcomes, evidence, skills).",
        "4. Refuse to claim scope above each accomplishment's seniority_ceiling.",
        "5. Recency-weight: bullets more than 7 years old should not score >0.7.",
        "6. Tie-break by accomplishment_id ascending.",
        "7. top_k_per_role MUST contain exactly the K best ids in score-desc order.",
        "8. Emit JSON conforming to the provided JSON schema. No prose.",
        "",
        f"LANE: {inputs.lane_slug}",
        f"K: {inputs.k}",
    ]
    if inputs.seniority_constraint:
        lines.append(f"SENIORITY CONSTRAINT: {inputs.seniority_constraint}")
    lines += [
        "",
        "JOB DESCRIPTION:",
        "----",
        inputs.jd_text.strip(),
        "----",
        "",
        "ACCOMPLISHMENTS (fact-only, no rendered bullets):",
        json.dumps(inputs.payload, indent=2, default=str),
        "",
        "JSON SCHEMA YOU MUST CONFORM TO:",
        json.dumps(RANKER_SCHEMA, indent=2),
    ]
    return "\n".join(lines)


# ── Response validation ─────────────────────────────────────────────────

@dataclass
class RankerValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    parsed: dict[str, Any] | None = None
    top_k: list[int] = field(default_factory=list)


def validate_ranker_response(
    response: str | dict[str, Any],
    *,
    expected_accomplishment_ids: set[int] | None = None,
    k: int | None = None,
) -> RankerValidationResult:
    """Validate Claude's structured response against the schema + sanity rules.

    `expected_accomplishment_ids`: if provided, every id in bullet_scores
    and top_k_per_role must come from this set (no hallucinated rows).
    `k`: if provided, top_k_per_role must have exactly this length.
    """
    errors: list[str] = []
    parsed: dict[str, Any] | None = None

    if isinstance(response, str):
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            return RankerValidationResult(
                valid=False,
                errors=[f"JSON decode error: {e}"],
            )
    elif isinstance(response, dict):
        parsed = response
    else:
        return RankerValidationResult(
            valid=False,
            errors=[f"Expected str or dict, got {type(response).__name__}"],
        )

    # Required fields
    for fld in ("jd_signals", "bullet_scores", "top_k_per_role"):
        if fld not in parsed:
            errors.append(f"missing required field '{fld}'")

    bullet_scores = parsed.get("bullet_scores") if parsed else None
    if not isinstance(bullet_scores, list):
        errors.append("bullet_scores must be a list")
        bullet_scores = []

    top_k = parsed.get("top_k_per_role") if parsed else None
    if not isinstance(top_k, list):
        errors.append("top_k_per_role must be a list")
        top_k = []

    if k is not None and len(top_k) != k:
        errors.append(f"top_k_per_role length {len(top_k)} != expected {k}")

    seen_ids: set[int] = set()
    for b in bullet_scores:
        if not isinstance(b, dict):
            errors.append(f"bullet_scores entry not a dict: {b!r}")
            continue
        a_id = b.get("accomplishment_id")
        score = b.get("score")
        if not isinstance(a_id, int):
            errors.append(f"accomplishment_id missing/not int: {b!r}")
        else:
            if expected_accomplishment_ids is not None and a_id not in expected_accomplishment_ids:
                errors.append(f"hallucinated accomplishment_id {a_id}")
            if a_id in seen_ids:
                errors.append(f"duplicate accomplishment_id {a_id}")
            seen_ids.add(a_id)
        if not isinstance(score, (int, float)) or not (0.0 <= float(score) <= 1.0):
            errors.append(f"score out of bounds for {a_id}: {score}")

    for tid in top_k:
        if not isinstance(tid, int):
            errors.append(f"top_k contains non-int: {tid!r}")
            continue
        if expected_accomplishment_ids is not None and tid not in expected_accomplishment_ids:
            errors.append(f"top_k contains hallucinated id {tid}")
        if tid not in seen_ids:
            errors.append(f"top_k id {tid} not in bullet_scores")

    return RankerValidationResult(
        valid=not errors,
        errors=errors,
        parsed=parsed,
        top_k=[int(t) for t in top_k if isinstance(t, int)],
    )
