"""Pure-Python fit scoring. No LLM calls.

Comp-first weighting per the advisory board's CRO verdict. Scoring runs on
Sean's canonical PROFILE (data/resumes/base.py) against either a raw scraped
role dict or a role row from pipeline.db.
"""

from __future__ import annotations

from config import FIT_SCORE_WEIGHTS, LANES, MIN_BASE_SALARY, MIN_TOTAL_COMP


def _skill_overlap(sean_skills: set[str], jd_skills: list[str]) -> float:
    """Return fraction of JD skills that appear in Sean's skill list (substring both ways)."""
    if not jd_skills:
        return 0.0
    jd = [s.lower() for s in jd_skills]
    hits = sum(
        1 for s in jd
        if any(s in sk or sk in s for sk in sean_skills)
    )
    return hits / len(jd)


def score_comp(comp_min: int | None, comp_max: int | None) -> float:
    """0-100. Explicit comp at/above MIN_BASE is 100; unverified is 55 (benefit of the doubt)."""
    if comp_min is None:
        return 55.0  # unverified — middle score, avoids dropping unknowns
    if comp_min >= MIN_TOTAL_COMP:
        return 100.0
    if comp_min >= MIN_BASE_SALARY:
        # linear between min-base and min-total-comp
        span = max(MIN_TOTAL_COMP - MIN_BASE_SALARY, 1)
        return 60.0 + 40.0 * (comp_min - MIN_BASE_SALARY) / span
    # below floor — penalize proportionally
    return max(0.0, 60.0 * comp_min / MIN_BASE_SALARY)


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
    # Partial credit if any single word overlaps
    lane_words = {w for kw in lane_cfg.get("title_keywords", []) for w in kw.split()}
    title_words = set(title_l.split())
    if lane_words & title_words:
        return 55.0
    return 25.0


def score_skills(parsed_jd_or_role: dict, lane: str, profile: dict) -> float:
    """Compare JD skills to Sean's profile skills; bonus for skills named in lane config."""
    sean_skills = {s.lower() for s in profile.get("skills", [])}
    required = parsed_jd_or_role.get("required_skills") or []
    preferred = parsed_jd_or_role.get("preferred_skills") or []

    if not required and not preferred:
        # No parsed JD yet — use lane skill_keywords heuristic on scraped title
        lane_cfg = LANES.get(lane, {})
        lane_skills = lane_cfg.get("skill_keywords", [])
        return 100.0 * _skill_overlap(sean_skills, lane_skills[:5])

    req = _skill_overlap(sean_skills, required)
    pref = _skill_overlap(sean_skills, preferred) if preferred else req
    return 100.0 * (0.7 * req + 0.3 * pref)


def score_remote(role: dict) -> float:
    if role.get("remote"):
        return 100.0
    loc = (role.get("location") or "").lower()
    if any(w in loc for w in ("remote", "anywhere", "distributed")):
        return 100.0
    if any(w in loc for w in ("hybrid",)):
        return 70.0
    return 30.0


def score_fit(role: dict, lane: str, parsed_jd: dict | None = None, profile: dict | None = None) -> float:
    """Return 0-100 composite fit score.

    `role` is a dict with keys like comp_min, comp_max, title, location, remote.
    `parsed_jd` is optional — if absent, we fall back to lane skill_keywords.
    `profile` defaults to data.resumes.base.PROFILE.
    """
    if profile is None:
        from data.resumes.base import PROFILE  # lazy import
        profile = PROFILE

    jd = parsed_jd or role

    w = FIT_SCORE_WEIGHTS
    # Use DB comp_min/max first; fall back to parsed JD when comp_explicit is True.
    comp_min = role.get("comp_min") or (parsed_jd.get("comp_min") if parsed_jd and parsed_jd.get("comp_explicit") else None)
    comp_max = role.get("comp_max") or (parsed_jd.get("comp_max") if parsed_jd and parsed_jd.get("comp_explicit") else None)
    comp = score_comp(comp_min, comp_max)
    title = score_title(role.get("title"), lane)
    skills = score_skills(jd, lane, profile)
    remote = score_remote(role)

    composite = (
        comp * w["comp"]
        + skills * w["skill_match"]
        + title * w["title_match"]
        + remote * w["remote"]
    )
    return round(composite, 1)
