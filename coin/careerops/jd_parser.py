"""JD keyword extractor — fills the `jd_keyword` table for a given role.

Two-stage pipeline:
  1. **Deterministic skill lookup** — match the JD text against the
     Lightcast skill subset (`careerops.skill_tagger.deterministic_skill_match`).
     Skills found get marked `must_have` if they appear in the
     "Requirements" / "Required" / "Must have" sections, else `nice_to_have`.
  2. **Claude-suggested signals (structured output)** — for the remaining
     "soft" keywords (industry terms, role-specific verbs, comp band,
     seniority cap), Claude extracts via the schema below.

This module does NOT call the LLM. It defines the prompt + validates
the response. modes/score.md drives execution.
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


# ── Section heading detection (Required / Nice-to-have) ─────────────────

_REQUIRED_HEADERS = (
    "requirements",
    "required",
    "must have",
    "must-have",
    "what you'll bring",
    "what you bring",
    "qualifications",
    "minimum qualifications",
    "basic qualifications",
)
_NICE_HEADERS = (
    "nice to have",
    "nice-to-have",
    "preferred",
    "preferred qualifications",
    "bonus",
    "plus",
)


def _classify_term_kind(jd_text: str, found_phrase: str) -> str:
    """Heuristic: look 200 chars before the phrase for a known section header."""
    pos = jd_text.lower().find(found_phrase.lower())
    if pos < 0:
        return "must_have"
    window = jd_text.lower()[max(0, pos - 800):pos]
    # Most-recent header wins.
    last_header_pos = -1
    last_header_kind = "must_have"
    for hdr in _REQUIRED_HEADERS:
        idx = window.rfind(hdr)
        if idx > last_header_pos:
            last_header_pos = idx
            last_header_kind = "must_have"
    for hdr in _NICE_HEADERS:
        idx = window.rfind(hdr)
        if idx > last_header_pos:
            last_header_pos = idx
            last_header_kind = "nice_to_have"
    return last_header_kind


# ── Stage 1: deterministic skill extraction ─────────────────────────────

@dataclass
class JdSkillHit:
    term: str
    term_kind: str           # 'must_have' | 'nice_to_have' | 'industry' | 'tool'
    importance: int          # 1..10
    lightcast_id: str | None
    skill_slug: str | None


def extract_skills_from_jd(
    jd_text: str,
    *,
    all_skills: list[dict],
) -> list[JdSkillHit]:
    """Run skill_tagger.deterministic_skill_match against the JD."""
    from careerops.skill_tagger import deterministic_skill_match
    matches = deterministic_skill_match(jd_text, all_skills=all_skills)
    out: list[JdSkillHit] = []
    for m in matches:
        kind = _classify_term_kind(jd_text, m.matched_phrase)
        # Importance: weight from skill_tagger × 1.25 (so weight 8 → 10).
        importance = min(10, max(1, int(round(m.weight * 1.25))))
        out.append(JdSkillHit(
            term=m.skill_name,
            term_kind=kind,
            importance=importance,
            lightcast_id=None,  # filled by caller via skill table lookup
            skill_slug=m.skill_slug,
        ))
    return out


# ── Stage 2: Claude-extracted soft signals ──────────────────────────────

JD_SIGNAL_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "CoinJdSignals",
    "type": "object",
    "required": ["seniority_cap", "comp_band", "industry_keywords", "role_verbs"],
    "additionalProperties": False,
    "properties": {
        "seniority_cap": {
            "type": ["string", "null"],
            "description": "Highest title-level the JD targets, e.g. 'Senior', 'Staff', 'Principal', or null if undefined.",
        },
        "comp_band": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "low": {"type": ["number", "null"]},
                "high": {"type": ["number", "null"]},
                "currency": {"type": ["string", "null"]},
                "explicit_in_jd": {"type": "boolean"},
            },
        },
        "industry_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Industry/domain terms (e.g. 'fintech', 'IoT', 'consumer hardware').",
        },
        "role_verbs": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Action verbs from the JD's responsibility list (e.g. 'orchestrate', 'lead', 'architect').",
        },
        "remote_friendly": {
            "type": ["boolean", "null"],
        },
        "company_stage": {
            "type": ["string", "null"],
            "description": "e.g. 'Series A', 'Series C', 'Public', null if unstated",
        },
    },
}


@dataclass
class JdSignalsPromptInputs:
    jd_text: str


def build_jd_signals_prompt(inputs: JdSignalsPromptInputs) -> str:
    return "\n".join([
        "Extract structured signals from this job description. Emit ONLY JSON conforming to the schema.",
        "",
        "RULES:",
        "1. seniority_cap: pick the most senior title mentioned ('Senior', 'Staff', 'Principal', 'Director', 'VP'). Null if unstated.",
        "2. comp_band: pull explicit base-salary numbers if present. Set explicit_in_jd=true only if the JD literally states a range. Otherwise leave low/high null and set explicit_in_jd=false.",
        "3. industry_keywords: domain/industry tags only ('fintech', 'IoT', 'B2B SaaS'). Do NOT include skills.",
        "4. role_verbs: top 5-10 action verbs from the responsibilities section.",
        "5. remote_friendly: true if 'remote' / 'work from anywhere' / 'distributed team' explicitly stated.",
        "6. company_stage: pull from 'Series X', 'pre-IPO', 'public company', etc. Null if absent.",
        "",
        "JOB DESCRIPTION:",
        "----",
        inputs.jd_text.strip(),
        "----",
        "",
        "JSON SCHEMA:",
        json.dumps(JD_SIGNAL_SCHEMA, indent=2),
    ])


@dataclass
class JdSignalsValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    parsed: dict | None = None


def validate_jd_signals_response(response: str | dict) -> JdSignalsValidationResult:
    if isinstance(response, str):
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            return JdSignalsValidationResult(valid=False, errors=[f"JSON decode error: {e}"])
    elif isinstance(response, dict):
        parsed = response
    else:
        return JdSignalsValidationResult(valid=False, errors=["response must be str|dict"])

    errors: list[str] = []
    for fld in ("seniority_cap", "comp_band", "industry_keywords", "role_verbs"):
        if fld not in parsed:
            errors.append(f"missing required field '{fld}'")

    industry = parsed.get("industry_keywords") if parsed else None
    if industry is not None and not isinstance(industry, list):
        errors.append("industry_keywords must be a list")
    role_verbs = parsed.get("role_verbs") if parsed else None
    if role_verbs is not None and not isinstance(role_verbs, list):
        errors.append("role_verbs must be a list")

    return JdSignalsValidationResult(valid=not errors, errors=errors, parsed=parsed)


# ── Persist to jd_keyword table ─────────────────────────────────────────

def persist_jd_signals(
    *,
    role_id: int,
    skill_hits: list[JdSkillHit],
    signals: dict | None = None,
    db_path: str | Path | None = None,
) -> int:
    """Write JD-extracted skills + signals into jd_keyword. Idempotent.

    Returns count of rows touched.
    """
    from careerops import experience as exp
    n = 0
    for hit in skill_hits:
        exp.upsert_jd_keyword(
            role_id=role_id,
            term=hit.term,
            term_kind=hit.term_kind,
            importance=hit.importance,
            lightcast_id=hit.lightcast_id,
            db_path=db_path,
        )
        n += 1
    if signals:
        # Industry keywords.
        for kw in signals.get("industry_keywords") or []:
            exp.upsert_jd_keyword(
                role_id=role_id,
                term=kw,
                term_kind="industry",
                importance=4,
                db_path=db_path,
            )
            n += 1
        # Role verbs are advisory; we don't persist them as keywords by default,
        # but the seniority_cap should be saved as an industry-class hint.
        sc = signals.get("seniority_cap")
        if sc:
            exp.upsert_jd_keyword(
                role_id=role_id,
                term=f"seniority:{sc}",
                term_kind="industry",
                importance=8,
                db_path=db_path,
            )
            n += 1
    return n
