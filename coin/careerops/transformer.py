"""Resume transformer — rewrites Sean's baseline for a specific lane and role."""

import json
import os
import anthropic
from datetime import datetime
from pathlib import Path
from config import CLAUDE_MODEL, LANES
from careerops.pipeline import get_role

_client = anthropic.Anthropic()

_SYSTEM = """\
You are an expert executive resume writer and career strategist.
You write in a direct, quantified, first-person style.
Never fabricate metrics. Only use data provided to you.
Never write generic summaries — every output must reference the specific company and role."""

_TRANSFORM_PROMPT = """\
Rewrite Sean Ivins' resume materials for the following target:

ROLE: {title} at {company}
LANE: {lane_label}
JD KEY REQUIREMENTS: {top_3}

SEAN'S CANONICAL PROFILE:
{profile_json}

LANE EMPHASIS STORIES (weight these highest):
{emphasis_stories}

Output JSON:
{{
  "executive_summary": "3-4 sentence paragraph, company-specific, quantified",
  "top_bullets": ["5 bullet points reweighted for this lane, each with a metric"],
  "skills_matched": ["skills from JD that Sean has"],
  "skills_gap": ["required skills Sean doesn't have — honest gaps"],
  "cover_letter_hook": "1 paragraph, specific to this role and company"
}}

Return ONLY valid JSON."""


def transform(lane: str, role_id: int) -> dict:
    role = get_role(role_id)
    if not role:
        raise ValueError(f"Role {role_id} not found")

    from data.resumes import base as base_module
    profile = base_module.PROFILE

    lane_cfg = LANES.get(lane, {})
    emphasis_keys = lane_cfg.get("emphasis", [])
    emphasis_stories = [
        story for story in profile.get("stories", [])
        if story.get("id") in emphasis_keys
    ]

    jd_parsed = json.loads(role.get("jd_parsed") or "{}")
    top_3 = jd_parsed.get("top_3_must_haves", ["see job description"])

    # Prompt caching: system + stable profile are cached; role-specific content is not
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
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
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(profile),
                        "cache_control": {"type": "ephemeral"},  # cache the large profile
                    },
                    {
                        "type": "text",
                        "text": _TRANSFORM_PROMPT.format(
                            title=role.get("title", ""),
                            company=role.get("company", ""),
                            lane_label=lane_cfg.get("label", lane),
                            top_3=", ".join(top_3),
                            profile_json="[see cached block above]",
                            emphasis_stories=json.dumps(emphasis_stories, indent=2),
                        ),
                    },
                ],
            }
        ],
    )

    result = json.loads(response.content[0].text)

    # Save output
    out_dir = Path("data/resumes/generated")
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    out_path = out_dir / f"{role_id}_{lane}_{date_str}.json"
    out_path.write_text(json.dumps(result, indent=2))

    return result
