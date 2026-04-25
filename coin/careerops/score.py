"""Pure-Python fit scoring. No LLM calls.

8-dimension scoring system with A-F letter grades.
Weights are sourced from config.FIT_SCORE_WEIGHTS — the docstring used to
embed numbers, but they drifted; trust config.py as the source of truth.

Current weights (2026-04-25):
  comp 0.28 · company_tier 0.20 · skill_match 0.22 · title_match 0.12
  remote 0.06 · application_effort 0.04 · seniority_fit 0.05 · culture_fit 0.03

Quarantine: roles with lane='out_of_band' (FAANG-tier pedigree filter)
short-circuit to composite=0, grade=F. See score_breakdown.
"""

from __future__ import annotations

from config import (
    FIT_SCORE_WEIGHTS, LANES, MIN_BASE_SALARY, MIN_TOTAL_COMP,
    COMPANY_TIERS, COMPANY_TIER_DEFAULT_SCORE, SCORE_GRADE_THRESHOLDS,
)


# ── Individual dimension scorers ──────────────────────────────────────────────

def score_comp(comp_min: int | None, comp_max: int | None) -> float:
    """0-100. Explicit comp at/above MIN_TC is 100; unverified is 55."""
    if comp_min is None:
        return 55.0
    if comp_min >= MIN_TOTAL_COMP:
        return 100.0
    if comp_min >= MIN_BASE_SALARY:
        span = max(MIN_TOTAL_COMP - MIN_BASE_SALARY, 1)
        return 60.0 + 40.0 * (comp_min - MIN_BASE_SALARY) / span
    return max(0.0, 60.0 * comp_min / MIN_BASE_SALARY)


def score_company_tier(company: str | None) -> float:
    """Score the role's company against COMPANY_TIERS (config.py).

    INVERTED for Sean's reality: tier1 = in-league mid-market / Utah tech (100),
    tier2 = recognized brand (75), tier4 = FAANG pedigree filter (25).
    Default for unknown small co = 65 (neutral, no penalty).

    Match rule: substring of the canonical name appears IN the company string
    (one direction only). Bidirectional matching previously caused false
    positives ('mx' in 'mxnet labs', 'roku' in 'rokumetrics').
    """
    if not company:
        return COMPANY_TIER_DEFAULT_SCORE
    c = company.lower().strip()
    for tier_cfg in COMPANY_TIERS.values():
        # One-direction substring: canonical name in company name only.
        # Tokenize on word boundary so 'mx' doesn't match 'mxnet' but 'mx' as
        # a standalone word does.
        for canonical in tier_cfg["companies"]:
            cn = canonical.lower()
            if cn == c or f" {cn} " in f" {c} " or c.startswith(f"{cn} ") or c.endswith(f" {cn}"):
                return tier_cfg["score"]
            # Also accept multi-word canonicals as substrings (e.g. "boston omaha")
            if " " in cn and cn in c:
                return tier_cfg["score"]
    return COMPANY_TIER_DEFAULT_SCORE


def score_title(title: str | None, lane: str) -> float:
    lane_cfg = LANES.get(lane, {})
    title_l = (title or "").lower()
    if not title_l:
        return 30.0
    for bad in lane_cfg.get("exclude_titles", []):
        if bad in title_l:
            return 0.0
    if any(kw in title_l for kw in lane_cfg.get("title_keywords", [])):
        return 100.0
    lane_words = {w for kw in lane_cfg.get("title_keywords", []) for w in kw.split()}
    if lane_words & set(title_l.split()):
        return 55.0
    return 25.0


def score_skills(parsed_jd_or_role: dict, lane: str, profile: dict) -> float:
    """Compare JD skills to Sean's profile. Falls back to lane keywords if no parsed JD."""
    sean_skills = {s.lower() for s in profile.get("skills", [])}
    required = parsed_jd_or_role.get("required_skills") or []
    preferred = parsed_jd_or_role.get("preferred_skills") or []

    if not required and not preferred:
        lane_cfg = LANES.get(lane, {})
        return 100.0 * _skill_overlap(sean_skills, lane_cfg.get("skill_keywords", [])[:5])

    req = _skill_overlap(sean_skills, required)
    pref = _skill_overlap(sean_skills, preferred) if preferred else req
    return 100.0 * (0.7 * req + 0.3 * pref)


def _skill_overlap(sean_skills: set[str], jd_skills: list[str]) -> float:
    if not jd_skills:
        return 0.0
    jd = [s.lower() for s in jd_skills]
    hits = sum(1 for s in jd if any(s in sk or sk in s for sk in sean_skills))
    return hits / len(jd)


def score_remote(role: dict) -> float:
    if role.get("remote"):
        return 100.0
    loc = (role.get("location") or "").lower()
    if any(w in loc for w in ("remote", "anywhere", "distributed")):
        return 100.0
    if "hybrid" in loc:
        return 70.0
    return 30.0


def score_application_effort(url: str | None) -> float:
    """100 = trivially easy, 65 = standard ATS, 40 = custom/unknown portal."""
    if not url:
        return 60.0
    u = url.lower()
    if "linkedin.com/jobs" in u:
        return 90.0
    if any(x in u for x in (
        "greenhouse.io", "lever.co", "workday.com", "ashbyhq.com",
        "rippling.com", "icims.com", "taleo.net", "smartrecruiters.com",
    )):
        return 65.0
    return 40.0


def score_seniority_fit(parsed_jd: dict | None) -> float:
    """100 = staff/principal/director (Sean's level), 80 = senior, 50 = unknown, 0 = junior."""
    if not parsed_jd:
        return 55.0
    level = (parsed_jd.get("seniority") or "").lower()
    if level in ("staff", "principal", "director", "vp", "lead"):
        return 100.0
    if level == "senior":
        return 80.0
    if level in ("mid", "manager", ""):
        return 50.0
    if level == "junior":
        return 0.0
    return 55.0


def score_culture_fit(parsed_jd: dict | None) -> float:
    """Start 80; deduct 10 per red flag; add 5 per positive culture signal. Clamp 0-100."""
    if not parsed_jd:
        return 60.0
    base = 80.0
    red_flags = parsed_jd.get("red_flags") or []
    culture_signals = parsed_jd.get("culture_signals") or []
    score = base - len(red_flags) * 10.0
    positives = {"collaborative", "flexible", "autonomy", "remote-first",
                 "distributed", "flat", "async", "transparent", "no micromanagement"}
    score += sum(5.0 for s in culture_signals if any(p in s.lower() for p in positives))
    return max(0.0, min(100.0, score))


# ── Grade ──────────────────────────────────────────────────────────────────────

def score_grade(score: float) -> str:
    for threshold, grade in SCORE_GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


# ── Composite ─────────────────────────────────────────────────────────────────

def score_fit(role: dict, lane: str, parsed_jd: dict | None = None, profile: dict | None = None) -> float:
    """Return 0-100 composite fit score across 8 dimensions."""
    return score_breakdown(role, lane, parsed_jd=parsed_jd, profile=profile)["composite"]


def score_breakdown(
    role: dict,
    lane: str,
    parsed_jd: dict | None = None,
    profile: dict | None = None,
) -> dict:
    """Return composite score + per-dimension breakdown dict.

    Shape:
      {
        "composite": 76.1,
        "grade": "B",
        "dimensions": {
          "comp":               {"raw": 100.0, "weight": 0.30, "contribution": 30.0},
          ...
        }
      }

    Quarantine guard: lane='out_of_band' (FAANG-tier pedigree filter) returns
    composite=0, grade=F immediately. Without this, LANES.get('out_of_band', {})
    returns {} and the per-dimension scorers fall through to defaults producing
    a 30-40 composite that resurrects quarantined roles in the dashboard.
    """
    if lane == "out_of_band" or lane not in LANES:
        return {
            "composite": 0.0,
            "grade": "F",
            "dimensions": {
                dim: {"raw": 0.0, "weight": w, "contribution": 0.0}
                for dim, w in FIT_SCORE_WEIGHTS.items()
            },
            "quarantined": True,
        }

    if profile is None:
        from data.resumes.base import PROFILE
        profile = PROFILE

    jd = parsed_jd or role
    w = FIT_SCORE_WEIGHTS

    # Comp: use DB row first; fall back to parsed_jd when comp_explicit is True
    comp_min = role.get("comp_min") or (
        parsed_jd.get("comp_min") if parsed_jd and parsed_jd.get("comp_explicit") else None
    )
    comp_max = role.get("comp_max") or (
        parsed_jd.get("comp_max") if parsed_jd and parsed_jd.get("comp_explicit") else None
    )

    raw = {
        "comp":               score_comp(comp_min, comp_max),
        "company_tier":       score_company_tier(role.get("company")),
        "skill_match":        score_skills(jd, lane, profile),
        "title_match":        score_title(role.get("title"), lane),
        "remote":             score_remote(role),
        "application_effort": score_application_effort(role.get("url")),
        "seniority_fit":      score_seniority_fit(parsed_jd),
        "culture_fit":        score_culture_fit(parsed_jd),
    }

    dimensions = {
        dim: {
            "raw": raw[dim],
            "weight": w[dim],
            "contribution": round(raw[dim] * w[dim], 1),
        }
        for dim in w
    }

    composite = round(sum(d["contribution"] for d in dimensions.values()), 1)

    return {
        "composite": composite,
        "grade": score_grade(composite),
        "dimensions": dimensions,
    }
