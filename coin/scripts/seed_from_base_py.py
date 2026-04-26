#!/usr/bin/env python
"""Seed the experience DB from data/resumes/base.py PROFILE (idempotent).

Reads:
  - data/resumes/base.py PROFILE (positions, bullets)
  - config/profile.yml (lanes, proof_points per lane)

Writes:
  - lane            (4 rows from profile.yml, upserted by slug)
  - accomplishment  (one row per bullet across all positions, ~10 rows;
                     idempotent by (position_slug, raw_text_source))
  - outcome         (auto-extracted metric tokens per bullet)
  - evidence        (one self_reported row per outcome, pointing to bullet)
  - accomplishment_lane (relevance per archetype using profile.yml proof_points
                        + heuristic match)

Re-running upserts. The CSV-driven m006 migration must run first; m005
runs implicitly (m006 bootstraps it).
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH


# ── Load PROFILE + profile.yml ────────────────────────────────────────────

def _load_profile():
    sys.path.insert(0, str(ROOT / "data" / "resumes"))
    from base import PROFILE  # type: ignore
    return PROFILE


def _load_profile_yml() -> dict:
    import yaml
    yml_path = ROOT / "config" / "profile.yml"
    return yaml.safe_load(yml_path.read_text()) or {}


# ── Numeric extractor (used by linter too — keep regex in sync) ──────────

# Currency: $1M, $27M, $1.5B, $500K, $1,000,000, $6M to $13M
_RE_CURRENCY = re.compile(
    r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(M|B|K)?\b",
    re.IGNORECASE,
)
# Percent: 40%, 73%, 99.97%
_RE_PERCENT = re.compile(r"\b(\d{1,3}(?:\.\d+)?)\s?%")
# Multiples: 4.2x, 10x
_RE_MULTIPLE = re.compile(r"\b(\d+(?:\.\d+)?)x\b", re.IGNORECASE)
# Year-1, Year 1
_RE_YEARS = re.compile(r"\b(?:Year|Y)\s?(\d+)\b", re.IGNORECASE)
# Generic counts with units we care about: 187 countries, 1,000+ pages, 7 localizations
_RE_COUNT_WITH_UNIT = re.compile(
    r"\b(\d{1,3}(?:,\d{3})*\+?)\s+(countries|pages|localizations|"
    r"deployments|sites|teams|engineers|customers|stakeholders|"
    r"continents|time zones|languages|regions|markets)\b",
    re.IGNORECASE,
)
# Time deltas: 12 months ahead of schedule, six weeks ahead, in under 2 years
_RE_TIME_DELTA = re.compile(
    r"\b(\d+|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+"
    r"(weeks?|months?|years?|days?)\b",
    re.IGNORECASE,
)


def _normalize_currency_to_numeric(amount: str, suffix: str | None) -> tuple[float, str]:
    """('27', 'M') -> (27_000_000.0, 'USD'). ('1,000,000', None) -> (1_000_000.0, 'USD')."""
    n = float(amount.replace(",", ""))
    s = (suffix or "").upper()
    mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(s, 1)
    return (n * mult, "USD")


def _extract_outcomes_from_bullet(bullet: str) -> list[dict]:
    """Best-effort extraction of quantified outcomes for seed purposes.

    Real life: Sean curates these via /coin add-evidence. The seed extractor
    just gives the migration something to start from so the truth-gate
    doesn't fail-closed on day one.
    """
    found: list[dict] = []
    seen_text: set[str] = set()

    # Currency ranges (e.g., "$6M to $13M ARR") — emit BOTH endpoints.
    for m in re.finditer(
        r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(M|B|K)?\s+to\s+\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(M|B|K)?",
        bullet,
        re.IGNORECASE,
    ):
        a1, s1, a2, s2 = m.group(1), m.group(2), m.group(3), m.group(4)
        for amt, suf in ((a1, s1), (a2, s2)):
            text = f"${amt}{(suf or '').upper()}"
            if text in seen_text:
                continue
            seen_text.add(text)
            n, unit = _normalize_currency_to_numeric(amt, suf)
            found.append({
                "metric_name": "monetary milestone",
                "value_numeric": n,
                "value_text": text,
                "unit": unit,
                "direction": "absolute",
            })

    # Standalone currencies.
    for m in _RE_CURRENCY.finditer(bullet):
        amt, suf = m.group(1), m.group(2)
        text = f"${amt}{(suf or '').upper()}"
        if text in seen_text:
            continue
        seen_text.add(text)
        n, unit = _normalize_currency_to_numeric(amt, suf)
        found.append({
            "metric_name": "monetary milestone",
            "value_numeric": n,
            "value_text": text,
            "unit": unit,
            "direction": "absolute",
        })

    # Percentages.
    for m in _RE_PERCENT.finditer(bullet):
        text = f"{m.group(1)}%"
        if text in seen_text:
            continue
        seen_text.add(text)
        found.append({
            "metric_name": "percentage outcome",
            "value_numeric": float(m.group(1)),
            "value_text": text,
            "unit": "pct",
            "direction": "increase" if "improv" in bullet.lower() or "growth" in bullet.lower() else "absolute",
        })

    # Multiples (4.2x).
    for m in _RE_MULTIPLE.finditer(bullet):
        text = f"{m.group(1)}x"
        if text in seen_text:
            continue
        seen_text.add(text)
        found.append({
            "metric_name": "multiple outcome",
            "value_numeric": float(m.group(1)),
            "value_text": text,
            "unit": "x",
            "direction": "increase",
        })

    # Counts with units.
    for m in _RE_COUNT_WITH_UNIT.finditer(bullet):
        amt_raw, unit_word = m.group(1), m.group(2)
        text = f"{amt_raw} {unit_word}"
        if text in seen_text:
            continue
        seen_text.add(text)
        n = float(amt_raw.replace(",", "").replace("+", ""))
        found.append({
            "metric_name": f"count of {unit_word.lower()}",
            "value_numeric": n,
            "value_text": text,
            "unit": unit_word.lower(),
            "direction": "absolute",
        })

    # Time deltas (six weeks ahead of schedule).
    for m in _RE_TIME_DELTA.finditer(bullet):
        amt_raw, unit_word = m.group(1), m.group(2)
        text = f"{amt_raw} {unit_word}"
        if text in seen_text:
            continue
        seen_text.add(text)
        word_to_num = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                       "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}
        try:
            n = float(amt_raw)
        except ValueError:
            n = float(word_to_num.get(amt_raw.lower(), 0))
        if n == 0:
            continue
        found.append({
            "metric_name": f"time delta in {unit_word.lower()}",
            "value_numeric": n,
            "value_text": text,
            "unit": unit_word.lower(),
            "direction": "absolute",
        })

    return found


# ── Seniority + tone heuristics ──────────────────────────────────────────

_SENIORITY_HINTS = {
    "fractional COO": "fractional_coo",
    "co-owned": "co_owner",
    "managed complete program execution": "program_lead",
    "led mission-critical": "program_lead",
    "served as primary liaison": "program_lead",
    "orchestrate global engineering teams": "program_lead",
    "coordinated": "team_member",
    "managed enterprise client": "team_member",
    "implemented company-wide": "team_member",
}

def _infer_seniority(bullet: str) -> str:
    bl = bullet.lower()
    for hint, ceiling in _SENIORITY_HINTS.items():
        if hint.lower() in bl:
            return ceiling
    return "team_member"


def _infer_tone(bullet: str) -> str:
    bl = bullet.lower()
    if any(w in bl for w in ("revenue", "arr", "series", "acquisition", "p&l", "client", "account")):
        return "commercial"
    if any(w in bl for w in ("rf", "wireless", "iot", "firmware", "embedded", "hardware")):
        return "technical"
    if any(w in bl for w in ("led", "managed", "orchestrate", "coordinate")):
        return "leadership"
    return "leadership"


def _bullet_title(bullet: str, max_chars: int = 60) -> str:
    """Short label — first clause (up to max_chars) ending at sensible punctuation."""
    head = bullet.split("—")[0].split(",")[0].strip()
    if len(head) > max_chars:
        head = head[:max_chars].rsplit(" ", 1)[0]
    return head


# ── Lane relevance ───────────────────────────────────────────────────────

# Map base.py story IDs to position slugs (mirrors PROFILE['stories']).
# Source of truth is PROFILE['stories'] but we hardcode a fallback so
# seeding works even if PROFILE is hand-edited and the 'stories' map drifts.
STORY_TO_POSITION = {
    "cox_true_local_labs": "hydrant",
    "titanx_fractional_coo": "hydrant",
    "safeguard_global_cms": "hydrant",
    "utah_broadband_acquisition": "utah_broadband",
    "arr_growth_6m_to_13m": "utah_broadband",
    "global_engineering_orchestration": "ca_engineering",
}

# Bullet substrings used as fingerprints to map a base.py bullet → story_id.
STORY_FINGERPRINTS = {
    "cox_true_local_labs": "cox communications",
    "titanx_fractional_coo": "fractional coo for titanx",
    "safeguard_global_cms": "safeguard global",
    "utah_broadband_acquisition": "boston omaha",
    "arr_growth_6m_to_13m": "$6m to $13m",
    "global_engineering_orchestration": "global engineering teams",
}


def _lane_relevances_for_bullet(bullet: str, lanes_yml: list[dict]) -> dict[str, int]:
    """Return {lane_slug: relevance_score 0-100} for one bullet.

    100 if the bullet's story_id is in the lane's proof_points.
    60-90 by keyword overlap heuristic against keyword_emphasis.
    Default 30 otherwise.
    """
    bl = bullet.lower()

    # Determine which story_id (if any) this bullet maps to.
    story_id = None
    for sid, fp in STORY_FINGERPRINTS.items():
        if fp.lower() in bl:
            story_id = sid
            break

    relevances: dict[str, int] = {}
    for lane in lanes_yml:
        slug = lane["id"]
        proof_points: list[str] = lane.get("proof_points", [])
        keyword_emphasis: list[str] = lane.get("keyword_emphasis", [])

        if story_id and story_id in proof_points:
            relevances[slug] = 100
            continue

        # Heuristic: count keyword_emphasis matches.
        hits = 0
        for kw in keyword_emphasis:
            if kw.lower() in bl:
                hits += 1
        if hits >= 3:
            score = 85
        elif hits == 2:
            score = 70
        elif hits == 1:
            score = 55
        else:
            score = 30
        relevances[slug] = score

    return relevances


# ── Seed entry points ────────────────────────────────────────────────────

def _archetypes_as_list(profile_yml: dict) -> list[dict]:
    """profile.yml stores archetypes as a dict keyed by slug. Normalize to a
    list of dicts where each carries an 'id' field equal to the slug."""
    archetypes = profile_yml.get("archetypes", {}) or {}
    if isinstance(archetypes, dict):
        return [{"id": slug, **(meta or {})} for slug, meta in archetypes.items()]
    return list(archetypes)


def _seed_lanes(conn: sqlite3.Connection, profile_yml: dict) -> int:
    lanes = _archetypes_as_list(profile_yml)
    n = 0
    for i, lane in enumerate(lanes, start=1):
        slug = lane["id"]
        label = lane.get("label", slug)
        rank = lane.get("rank", i)
        conn.execute(
            """
            INSERT INTO lane (slug, label, rank) VALUES (?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                label = excluded.label,
                rank = excluded.rank
            """,
            (slug, label, rank),
        )
        n += 1
    return n


def _seed_accomplishments(
    conn: sqlite3.Connection, profile: dict, lanes_yml: list[dict]
) -> tuple[int, int, int, int]:
    """Returns (acc_count, outcome_count, evidence_count, lane_link_count)."""
    acc_n = out_n = ev_n = lane_n = 0

    # Lane lookup by slug.
    lane_id_by_slug: dict[str, int] = {
        row[0]: row[1]
        for row in conn.execute("SELECT slug, id FROM lane").fetchall()
    }

    for position in profile.get("positions", []):
        position_slug = position["id"]
        time_period_start = position.get("start")
        time_period_end = position.get("end")
        for bullet in position.get("bullets", []):
            title = _bullet_title(bullet)
            seniority = _infer_seniority(bullet)
            tone = _infer_tone(bullet)

            # Idempotency: dedup by (position_slug, raw_text_source).
            existing = conn.execute(
                "SELECT id FROM accomplishment WHERE position_slug=? AND raw_text_source=?",
                (position_slug, bullet),
            ).fetchone()
            if existing:
                acc_id = existing[0]
                conn.execute(
                    """UPDATE accomplishment SET
                          title=?, time_period_start=?, time_period_end=?,
                          seniority_ceiling=?, narrative_tone=?,
                          updated_at=datetime('now')
                       WHERE id=?""",
                    (title, time_period_start, time_period_end, seniority, tone, acc_id),
                )
            else:
                cur = conn.execute(
                    """INSERT INTO accomplishment (
                          position_slug, title, time_period_start, time_period_end,
                          situation, task, action, result,
                          seniority_ceiling, narrative_tone, raw_text_source
                       ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        position_slug, title, time_period_start, time_period_end,
                        None, None, None, bullet,
                        seniority, tone, bullet,
                    ),
                )
                acc_id = cur.lastrowid
                acc_n += 1

            # Outcomes: extract metric tokens.
            outcomes = _extract_outcomes_from_bullet(bullet)
            for o in outcomes:
                # Dedup by (accomplishment_id, value_text, metric_name).
                existing_o = conn.execute(
                    "SELECT id FROM outcome WHERE accomplishment_id=? AND value_text=? AND metric_name=?",
                    (acc_id, o["value_text"], o["metric_name"]),
                ).fetchone()
                if existing_o:
                    out_id = existing_o[0]
                else:
                    cur = conn.execute(
                        """INSERT INTO outcome (
                              accomplishment_id, metric_name, value_numeric,
                              value_text, unit, direction
                           ) VALUES (?, ?, ?, ?, ?, ?)""",
                        (acc_id, o["metric_name"], o["value_numeric"],
                         o["value_text"], o["unit"], o["direction"]),
                    )
                    out_id = cur.lastrowid
                    out_n += 1

                # Evidence: one self_reported row per outcome (idempotent).
                existing_ev = conn.execute(
                    "SELECT id FROM evidence WHERE outcome_id=? AND source='self_reported'",
                    (out_id,),
                ).fetchone()
                if not existing_ev:
                    notes = (
                        f"Seeded from data/resumes/base.py — position '{position_slug}', "
                        f"bullet: {bullet[:160]}"
                    )
                    conn.execute(
                        """INSERT INTO evidence (
                              outcome_id, kind, source, url_or_path, notes
                           ) VALUES (?, ?, ?, ?, ?)""",
                        (out_id, "metric", "self_reported", None, notes),
                    )
                    ev_n += 1

            # Lane relevance.
            relevances = _lane_relevances_for_bullet(bullet, lanes_yml)
            for slug, score in relevances.items():
                lane_id = lane_id_by_slug.get(slug)
                if lane_id is None:
                    continue
                conn.execute(
                    """INSERT INTO accomplishment_lane (
                          accomplishment_id, lane_id, relevance_score, manual_pin
                       ) VALUES (?, ?, ?, 0)
                       ON CONFLICT(accomplishment_id, lane_id) DO UPDATE SET
                          relevance_score = CASE
                              WHEN accomplishment_lane.manual_pin = 1
                              THEN accomplishment_lane.relevance_score
                              ELSE excluded.relevance_score
                          END""",
                    (acc_id, lane_id, score),
                )
                lane_n += 1

    return (acc_n, out_n, ev_n, lane_n)


def seed(db_path: str | Path) -> dict[str, int]:
    """Public entrypoint. Returns a stats dict."""
    db_path = Path(db_path)

    # Run m005 + m006 first (they bootstrap each other / are idempotent).
    from scripts.migrations import m005_experience_db as m005
    from scripts.migrations import m006_seed_lightcast as m006
    m005.apply(db_path)
    m006.apply(db_path)

    profile = _load_profile()
    profile_yml = _load_profile_yml()
    lanes_yml = _archetypes_as_list(profile_yml)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        lanes_n = _seed_lanes(conn, profile_yml)
        acc_n, out_n, ev_n, lane_n = _seed_accomplishments(conn, profile, lanes_yml)
        conn.commit()
    finally:
        conn.close()

    return {
        "lanes": lanes_n,
        "accomplishments_inserted": acc_n,
        "outcomes_inserted": out_n,
        "evidence_inserted": ev_n,
        "lane_links_touched": lane_n,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=None, help="Override DB path (defaults to config.DB_PATH)")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else (ROOT / DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    stats = seed(db_path)
    print("✅ Seed complete:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
