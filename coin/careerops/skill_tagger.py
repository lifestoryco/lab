"""Skill tagger — match accomplishment text to Lightcast skill IDs.

Two paths:
  1. **Deterministic substring match** — scan accomplishment text against
     all skill names + slug forms. Hits go straight to accomplishment_skill.
     Fast, 100% reproducible, no LLM call. Catches the obvious overlaps.
  2. **Claude-suggested tags (structured output)** — for accomplishments
     where the deterministic path returns <3 hits, build a prompt that
     asks Claude to suggest Lightcast IDs from a candidate list.

The structured-output schema lives below. modes/capture.md uses it; this
module just defines the contract.

Designed around the principle that we never let Claude invent skill names
out of thin air — Claude only PICKS from the candidate list returned by
the deterministic preselection.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── Deterministic substring matcher ─────────────────────────────────────

@dataclass
class SkillMatch:
    skill_slug: str
    skill_name: str
    weight: int             # 1..10
    matched_phrase: str     # surface form found in text


def deterministic_skill_match(
    text: str,
    *,
    all_skills: list[dict],
    min_phrase_len: int = 4,
) -> list[SkillMatch]:
    """Find every skill name/slug that appears as a substring in text.

    `all_skills` is a list of dicts with keys: slug, name (Lightcast row).
    Match is case-insensitive whole-phrase (word boundaries enforced).

    Weighting:
      - exact name match anywhere → weight 8
      - exact slug match (with hyphens-to-spaces) → weight 7
      - last-word-of-name match (e.g. 'Salesforce' from 'Salesforce CPQ') → weight 5

    Skills shorter than `min_phrase_len` chars are skipped (too noisy).
    """
    if not text:
        return []

    text_l = text.lower()
    seen_slugs: set[str] = set()
    out: list[SkillMatch] = []

    for skill in all_skills:
        slug = (skill.get("slug") or "").strip()
        name = (skill.get("name") or "").strip()
        if not slug or not name or len(name) < min_phrase_len:
            continue

        # Try the canonical name first (most specific).
        if _phrase_in_text(name, text_l):
            if slug not in seen_slugs:
                out.append(SkillMatch(
                    skill_slug=slug, skill_name=name, weight=8, matched_phrase=name,
                ))
                seen_slugs.add(slug)
            continue

        # Try the slug as space-separated phrase.
        slug_phrase = slug.replace("-", " ")
        if len(slug_phrase) >= min_phrase_len and _phrase_in_text(slug_phrase, text_l):
            if slug not in seen_slugs:
                out.append(SkillMatch(
                    skill_slug=slug, skill_name=name, weight=7, matched_phrase=slug_phrase,
                ))
                seen_slugs.add(slug)

    return out


def _phrase_in_text(phrase: str, text_lower: str) -> bool:
    pl = phrase.lower()
    pat = r"(?<!\w)" + re.escape(pl) + r"(?!\w)"
    return bool(re.search(pat, text_lower))


# ── Claude-prompt schema for ambiguous cases ────────────────────────────

SKILL_TAG_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CoinSkillTagSuggestion",
    "type": "object",
    "required": ["suggestions"],
    "additionalProperties": False,
    "properties": {
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["skill_slug", "weight", "rationale"],
                "additionalProperties": False,
                "properties": {
                    "skill_slug": {
                        "type": "string",
                        "description": "MUST appear in the candidate_skills list provided.",
                    },
                    "weight": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "rationale": {"type": "string"},
                },
            },
        },
    },
}


@dataclass
class SkillTagPromptInputs:
    accomplishment_text: str
    candidate_skills: list[dict]   # subset of skill rows to choose from
    seniority_ceiling: str | None = None


def build_skill_tag_prompt(inputs: SkillTagPromptInputs) -> str:
    body = [
        "You are coin's skill tagger. Pick which Lightcast skills the "
        "given accomplishment demonstrates.",
        "",
        "RULES:",
        "1. ONLY suggest skill_slug values from candidate_skills.",
        "2. Weight 1-10: 8-10 = primary skill demonstrated; 5-7 = supporting; 1-4 = adjacent.",
        "3. If no candidate genuinely fits, return suggestions=[] (empty).",
        "4. Each rationale cites which words in the accomplishment evidence the tag.",
        "5. Emit JSON conforming to the schema. No prose.",
        "",
        "ACCOMPLISHMENT:",
        inputs.accomplishment_text,
        "",
    ]
    if inputs.seniority_ceiling:
        body += [f"SENIORITY CEILING: {inputs.seniority_ceiling}", ""]
    body += [
        "CANDIDATE_SKILLS (you may only use these slugs):",
        json.dumps(
            [{"slug": s["slug"], "name": s["name"], "category": s.get("category")}
             for s in inputs.candidate_skills],
            indent=2,
        ),
        "",
        "JSON SCHEMA:",
        json.dumps(SKILL_TAG_SCHEMA, indent=2),
    ]
    return "\n".join(body)


@dataclass
class SkillTagValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    suggestions: list[dict] = field(default_factory=list)


def validate_skill_tag_response(
    response: str | dict,
    *,
    valid_slugs: set[str],
) -> SkillTagValidationResult:
    """Verify Claude's response is well-formed and slugs are real."""
    errors: list[str] = []
    if isinstance(response, str):
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            return SkillTagValidationResult(valid=False, errors=[f"JSON decode error: {e}"])
    elif isinstance(response, dict):
        parsed = response
    else:
        return SkillTagValidationResult(valid=False, errors=["response must be str|dict"])

    suggestions = parsed.get("suggestions")
    if not isinstance(suggestions, list):
        errors.append("'suggestions' must be a list")
        suggestions = []

    cleaned: list[dict] = []
    for s in suggestions:
        if not isinstance(s, dict):
            errors.append(f"non-dict suggestion: {s!r}")
            continue
        slug = s.get("skill_slug")
        weight = s.get("weight")
        if slug not in valid_slugs:
            errors.append(f"hallucinated slug: {slug!r}")
            continue
        if not isinstance(weight, int) or not (1 <= weight <= 10):
            errors.append(f"weight out of bounds for {slug}: {weight!r}")
            continue
        cleaned.append({
            "skill_slug": slug,
            "weight": weight,
            "rationale": s.get("rationale", ""),
        })

    return SkillTagValidationResult(
        valid=not errors,
        errors=errors,
        suggestions=cleaned,
    )
