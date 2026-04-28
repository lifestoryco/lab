"""STAR-format proof point library — load / add / update / query / validate.

Single source of truth for tailored resume bullets. Tailor (modes/tailor.md)
consults this first; falls back to data/resumes/base.py PROFILE only when
no story matches. Audit Check 5 (modes/audit.md) traces every metric in a
generated bullet back to a story id here.

All write paths are atomic (tempfile in same dir → fsync → os.replace).
No LLM calls; pure data API.
"""
from __future__ import annotations

import datetime as _dt
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

# Hard-coded canonical archetypes. Per CLAUDE.md / modes/_shared.md.
# Intentionally NOT loaded dynamically — we want validate_story to fail
# loudly if a future archetype refactor forgets to update this list.
VALID_LANES = {
    "mid-market-tpm",
    "enterprise-sales-engineer",
    "iot-solutions-architect",
    "revenue-ops-operator",
}

VALID_GRADES = {"A", "B", "C"}

_REPO_ROOT = Path(__file__).resolve().parents[1]
STORIES_PATH = Path(os.environ.get("COIN_STORIES_PATH", _REPO_ROOT / "data" / "resumes" / "stories.yml"))


# ── load / write ────────────────────────────────────────────────────────────

def _read_yaml() -> dict:
    if not STORIES_PATH.exists():
        return {"version": 1, "stories": []}
    try:
        with STORIES_PATH.open() as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"stories.yml is malformed YAML: {e}") from e
    if not isinstance(data, dict):
        raise ValueError(f"stories.yml top level must be a mapping, got {type(data).__name__}")
    data.setdefault("version", 1)
    data.setdefault("stories", [])
    if not isinstance(data["stories"], list):
        raise ValueError("stories.yml 'stories' must be a list")
    return data


def _atomic_write(data: dict) -> None:
    """Write stories.yml atomically with crash-consistent durability.

    Pattern: tempfile in same dir → write+fsync → os.replace → fsync parent.
    Same-dir tempfile keeps the rename within one filesystem; the parent-dir
    fsync ensures the directory entry is durable on power loss.

    NOTE: this is single-writer-only. Concurrent add_story/update_story
    callers can race the read-validate-write sequence and last-writer wins.
    The CLI is the sole writer in practice; the web tier is read-only on
    Vercel and gated through web_cli locally.
    """
    STORIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".stories.", suffix=".yml.tmp", dir=str(STORIES_PATH.parent))
    try:
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, STORIES_PATH)
        # Parent-dir fsync makes the rename durable on crash. Best-effort —
        # not every filesystem supports it (e.g. tmpfs).
        try:
            dir_fd = os.open(str(STORIES_PATH.parent), os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError:
            pass
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
        raise


def load_stories() -> list[dict]:
    """Read stories.yml, validate top-level shape, return list of story dicts.

    Raises ValueError on malformed YAML with a clear message.
    """
    return _read_yaml()["stories"]


def get_story_by_id(id: str) -> dict | None:
    for s in load_stories():
        if s.get("id") == id:
            return s
    return None


# ── validate ────────────────────────────────────────────────────────────────

_REQUIRED_FIELDS = (
    "id", "role", "dates", "lanes_relevant_for",
    "situation", "task", "action", "result",
    "metrics", "grade", "created", "last_validated",
)


def _is_yyyymm(value: Any) -> bool:
    if value == "present":
        return True
    if not isinstance(value, str):
        return False
    if len(value) != 7 or value[4] != "-":
        return False
    y, m = value[:4], value[5:]
    if not (y.isdigit() and m.isdigit()):
        return False
    month = int(m)
    return 1 <= month <= 12


def _is_yyyymmdd_or_date(value: Any) -> bool:
    if isinstance(value, _dt.date):
        return True
    if not isinstance(value, str):
        return False
    try:
        _dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_story(story: dict) -> tuple[bool, list[str]]:
    """Returns (valid, [error strings]). Empty error list iff valid."""
    errors: list[str] = []

    if not isinstance(story, dict):
        return False, [f"story must be a dict, got {type(story).__name__}"]

    for field in _REQUIRED_FIELDS:
        if field not in story:
            errors.append(f"missing required field: {field}")

    # id
    if "id" in story and not (isinstance(story["id"], str) and story["id"].strip()):
        errors.append("id must be a non-empty string")

    # dates
    dates = story.get("dates")
    if isinstance(dates, dict):
        if "start" not in dates or not _is_yyyymm(dates["start"]):
            errors.append("dates.start must be YYYY-MM")
        if "end" not in dates or not _is_yyyymm(dates["end"]):
            errors.append("dates.end must be YYYY-MM or 'present'")
    elif "dates" in story:
        errors.append("dates must be a mapping with 'start' and 'end'")

    # lanes
    lanes = story.get("lanes_relevant_for")
    if isinstance(lanes, list):
        for ln in lanes:
            if ln not in VALID_LANES:
                errors.append(f"invalid lane: {ln} (valid: {sorted(VALID_LANES)})")
    elif "lanes_relevant_for" in story:
        errors.append("lanes_relevant_for must be a list")

    # grade
    if "grade" in story and story["grade"] not in VALID_GRADES:
        errors.append(f"grade must be one of {sorted(VALID_GRADES)}, got {story['grade']!r}")

    # metrics
    metrics = story.get("metrics")
    if isinstance(metrics, list):
        for i, m in enumerate(metrics):
            if not isinstance(m, dict):
                errors.append(f"metrics[{i}] must be a dict")
                continue
            for k in ("value", "unit", "description"):
                if k not in m:
                    errors.append(f"metrics[{i}] missing {k}")
    elif "metrics" in story:
        errors.append("metrics must be a list")

    # last_validated / created
    for date_field in ("created", "last_validated"):
        if date_field in story and not _is_yyyymmdd_or_date(story[date_field]):
            errors.append(f"{date_field} must be a YYYY-MM-DD date")

    return (not errors, errors)


# ── mutate ──────────────────────────────────────────────────────────────────

def add_story(story: dict) -> str:
    """Validate, append, atomic-write. Returns story id."""
    valid, errors = validate_story(story)
    if not valid:
        raise ValueError("invalid story: " + "; ".join(errors))

    data = _read_yaml()
    if any(s.get("id") == story["id"] for s in data["stories"]):
        raise ValueError(f"duplicate story id: {story['id']}")

    data["stories"].append(story)
    _atomic_write(data)
    return story["id"]


def update_story(id: str, partial: dict) -> bool:
    """Merge partial into the story with this id. Atomic write.

    Does NOT clobber unspecified fields (shallow merge per top-level key).
    Returns True on success, False if id missing.
    """
    data = _read_yaml()
    for i, s in enumerate(data["stories"]):
        if s.get("id") == id:
            merged = {**s, **partial, "id": s["id"]}  # protect id from rename
            valid, errors = validate_story(merged)
            if not valid:
                raise ValueError("invalid story after merge: " + "; ".join(errors))
            data["stories"][i] = merged
            _atomic_write(data)
            return True
    return False


# ── query ───────────────────────────────────────────────────────────────────

_GRADE_WEIGHT = {"A": 3, "B": 2, "C": 1}
_RECENCY_DAYS_THRESHOLD = 730  # 2 years


def _grade_at_least(grade: str, minimum: str) -> bool:
    return _GRADE_WEIGHT.get(grade, 0) >= _GRADE_WEIGHT.get(minimum, 0)


def _today() -> _dt.date:
    """Indirection so tests can monkeypatch this without touching datetime.date."""
    return _dt.date.today()


def _recency_factor(last_validated: Any) -> float:
    if isinstance(last_validated, _dt.date):
        d = last_validated
    else:
        try:
            d = _dt.date.fromisoformat(str(last_validated))
        except (TypeError, ValueError):
            return 0.5
    age_days = (_today() - d).days
    # Inclusive at the boundary so a story validated exactly _RECENCY_DAYS_THRESHOLD
    # days ago still counts as "recent" — matches the docstring "within 2 years".
    return 1.0 if age_days <= _RECENCY_DAYS_THRESHOLD else 0.5


def find_stories_for_lane(lane: str, min_grade: str = "B") -> list[dict]:
    """Filter by lane in story.lanes_relevant_for AND grade >= min_grade.

    Sorted by grade desc then last_validated desc.
    """
    out = [
        s for s in load_stories()
        if lane in (s.get("lanes_relevant_for") or [])
        and _grade_at_least(s.get("grade", "C"), min_grade)
    ]
    out.sort(
        key=lambda s: (
            _GRADE_WEIGHT.get(s.get("grade", "C"), 0),
            str(s.get("last_validated") or ""),
        ),
        reverse=True,
    )
    return out


def find_stories_for_skills(
    skills: list[str],
    lane: str | None = None,
) -> list[dict]:
    """Rank by (skill overlap count) * (grade weight) * (recency factor).

    Optionally pre-filter by lane. Stories with zero overlap are excluded.
    """
    skill_set = {s.lower() for s in skills}
    pool = load_stories()
    if lane is not None:
        pool = [s for s in pool if lane in (s.get("lanes_relevant_for") or [])]

    scored = []
    for story in pool:
        story_skills = {s.lower() for s in (story.get("related_skills") or [])}
        overlap = len(skill_set & story_skills)
        if overlap == 0:
            continue
        grade_w = _GRADE_WEIGHT.get(story.get("grade", "C"), 0)
        recency = _recency_factor(story.get("last_validated"))
        score = overlap * grade_w * recency
        scored.append((score, story))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [s for _, s in scored]
