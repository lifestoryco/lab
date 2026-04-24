"""JD analyzer — uses Claude to extract skills, comp signals, and fit score."""

import json
import os
import anthropic
from config import CLAUDE_MODEL, LANES
from careerops.pipeline import get_role, update_jd_parsed
from careerops.scraper import fetch_jd

_client = anthropic.Anthropic()

_SYSTEM = """\
You are a career intelligence analyst. Given a job description, extract structured data.
Return ONLY valid JSON — no markdown, no prose."""

_PARSE_PROMPT = """\
Extract the following from this job description and return as JSON:

{
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "comp_min": integer_or_null,
  "comp_max": integer_or_null,
  "comp_explicit": boolean,
  "remote": boolean,
  "seniority": "junior|mid|senior|staff|principal|director",
  "yoe_min": integer_or_null,
  "culture_signals": ["string"],
  "top_3_must_haves": ["string"]
}

Job description:
{jd}"""


def parse_jd(role_id: int) -> dict:
    role = get_role(role_id)
    if not role:
        raise ValueError(f"Role {role_id} not found in pipeline")

    jd_raw = role.get("jd_raw") or fetch_jd(role["url"])

    # Use prompt caching — system + base prompt are stable across calls
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": _SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": _PARSE_PROMPT.format(jd=jd_raw[:6000]),
            }
        ],
    )

    parsed = json.loads(response.content[0].text)
    update_jd_parsed(role_id, parsed)
    return parsed


def score_fit(role: dict, lane: str, parsed_jd: dict) -> float:
    """Return a 0–100 fit score for Sean against this role."""
    from data.resumes.base import PROFILE

    lane_cfg = LANES.get(lane, {})
    emphasis_stories = lane_cfg.get("emphasis", [])

    # Skill match: what fraction of required skills appear in Sean's skills
    sean_skills = {s.lower() for s in PROFILE.get("skills", [])}
    required = [s.lower() for s in parsed_jd.get("required_skills", [])]
    preferred = [s.lower() for s in parsed_jd.get("preferred_skills", [])]

    req_match = sum(1 for s in required if any(s in sk or sk in s for sk in sean_skills))
    pref_match = sum(1 for s in preferred if any(s in sk or sk in s for sk in sean_skills))

    skill_score = 0.0
    if required:
        skill_score = (req_match / len(required)) * 70 + (pref_match / max(len(preferred), 1)) * 30

    # Title match: does lane's title keywords appear in role title?
    title = (role.get("title") or "").lower()
    title_keywords = lane_cfg.get("title_keywords", [])
    title_score = 100.0 if any(kw in title for kw in title_keywords) else 40.0

    # Comp score: is comp band at or above minimum?
    comp_min = parsed_jd.get("comp_min") or role.get("comp_min") or 0
    from config import MIN_BASE_SALARY
    comp_score = 100.0 if comp_min >= MIN_BASE_SALARY else max(0.0, (comp_min / MIN_BASE_SALARY) * 100)

    # Weighted composite
    return round(
        title_score * 0.30 +
        skill_score * 0.45 +
        comp_score  * 0.25,
        1,
    )
