"""Read/write API for the experience DB (m005 + m006 tables).

Consumed by:
- modes/tailor.md  (reads accomplishments + outcomes per role/lane)
- modes/audit.md   (truthfulness Check 10: metric ↔ outcome row)
- modes/cover-letter.md (same truth-gate, same DB)
- modes/capture.md (writes new STAR-format accomplishments)
- modes/recruiter-eye.md (queries lane → top-K bullets)
- careerops/ranker.py (top-K candidates per role/lane)
- careerops/score_panel.py (keyword overlap, truth-gate verification)
- scripts/render_resume.py (multi-variant orchestrator)
- scripts/add_evidence.py (CLI to upgrade evidence)

Design rules:
- Every read returns sqlite3.Row (dict-style access by column name).
- Every write is idempotent where the schema's UNIQUE/PRIMARY KEY allows
  ON CONFLICT semantics; otherwise dedup is checked explicitly.
- No business logic here — just data plumbing. Truthfulness/density
  enforcement lives in careerops/linter.py.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH


# ── Connection helper ────────────────────────────────────────────────────

def _conn(db_path: str | Path | None = None) -> sqlite3.Connection:
    p = Path(db_path) if db_path else Path(DB_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Lane queries ─────────────────────────────────────────────────────────

def get_lane_by_slug(slug: str, *, db_path: str | Path | None = None) -> sqlite3.Row | None:
    with _conn(db_path) as conn:
        return conn.execute("SELECT * FROM lane WHERE slug=?", (slug,)).fetchone()


def list_lanes(*, db_path: str | Path | None = None) -> list[sqlite3.Row]:
    with _conn(db_path) as conn:
        return list(conn.execute("SELECT * FROM lane ORDER BY rank, slug").fetchall())


# ── Accomplishment queries ───────────────────────────────────────────────

def get_accomplishment(acc_id: int, *, db_path: str | Path | None = None) -> sqlite3.Row | None:
    with _conn(db_path) as conn:
        return conn.execute(
            "SELECT * FROM accomplishment WHERE id=?", (acc_id,)
        ).fetchone()


def list_accomplishments(
    *,
    position_slug: str | None = None,
    seniority_ceiling: str | None = None,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM accomplishment WHERE 1=1"
    args: list[Any] = []
    if position_slug:
        sql += " AND position_slug=?"
        args.append(position_slug)
    if seniority_ceiling:
        sql += " AND seniority_ceiling=?"
        args.append(seniority_ceiling)
    sql += " ORDER BY position_slug, id"
    with _conn(db_path) as conn:
        return list(conn.execute(sql, args).fetchall())


def list_accomplishments_for_lane(
    lane_slug: str,
    *,
    min_relevance: int = 30,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    """All accomplishments tagged for a lane, ordered by relevance desc."""
    with _conn(db_path) as conn:
        return list(conn.execute(
            """
            SELECT a.*, al.relevance_score, al.manual_pin
            FROM accomplishment a
            JOIN accomplishment_lane al ON al.accomplishment_id = a.id
            JOIN lane l ON l.id = al.lane_id
            WHERE l.slug = ? AND al.relevance_score >= ?
            ORDER BY al.relevance_score DESC, a.position_slug, a.id
            """,
            (lane_slug, min_relevance),
        ).fetchall())


def upsert_accomplishment(
    *,
    position_slug: str,
    title: str,
    raw_text_source: str,
    time_period_start: str | None = None,
    time_period_end: str | None = None,
    situation: str | None = None,
    task: str | None = None,
    action: str | None = None,
    result: str | None = None,
    seniority_ceiling: str | None = None,
    narrative_tone: str | None = None,
    linter_override: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    """Idempotent on (position_slug, raw_text_source). Returns accomplishment id."""
    with _conn(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM accomplishment WHERE position_slug=? AND raw_text_source=?",
            (position_slug, raw_text_source),
        ).fetchone()
        if existing:
            acc_id = existing["id"]
            conn.execute(
                """UPDATE accomplishment SET
                      title=?, time_period_start=?, time_period_end=?,
                      situation=?, task=?, action=?, result=?,
                      seniority_ceiling=?, narrative_tone=?,
                      linter_override=?, updated_at=datetime('now')
                   WHERE id=?""",
                (title, time_period_start, time_period_end,
                 situation, task, action, result,
                 seniority_ceiling, narrative_tone, linter_override, acc_id),
            )
            conn.commit()
            return acc_id
        cur = conn.execute(
            """INSERT INTO accomplishment (
                  position_slug, title, time_period_start, time_period_end,
                  situation, task, action, result,
                  seniority_ceiling, narrative_tone, raw_text_source, linter_override
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (position_slug, title, time_period_start, time_period_end,
             situation, task, action, result,
             seniority_ceiling, narrative_tone, raw_text_source, linter_override),
        )
        conn.commit()
        return cur.lastrowid


# ── Outcome queries ──────────────────────────────────────────────────────

def list_outcomes(
    accomplishment_id: int,
    *,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    with _conn(db_path) as conn:
        return list(conn.execute(
            "SELECT * FROM outcome WHERE accomplishment_id=? ORDER BY id",
            (accomplishment_id,),
        ).fetchall())


def insert_outcome(
    *,
    accomplishment_id: int,
    metric_name: str,
    value_text: str,
    value_numeric: float | None = None,
    unit: str | None = None,
    direction: str | None = None,
    asof_date: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    """Idempotent on (accomplishment_id, metric_name, value_text)."""
    with _conn(db_path) as conn:
        existing = conn.execute(
            """SELECT id FROM outcome
               WHERE accomplishment_id=? AND metric_name=? AND value_text=?""",
            (accomplishment_id, metric_name, value_text),
        ).fetchone()
        if existing:
            return existing["id"]
        cur = conn.execute(
            """INSERT INTO outcome (
                  accomplishment_id, metric_name, value_numeric,
                  value_text, unit, direction, asof_date
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (accomplishment_id, metric_name, value_numeric,
             value_text, unit, direction, asof_date),
        )
        conn.commit()
        return cur.lastrowid


# ── Evidence queries ─────────────────────────────────────────────────────

def list_evidence(
    *,
    outcome_id: int | None = None,
    accomplishment_id: int | None = None,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    if outcome_id is None and accomplishment_id is None:
        raise ValueError("Pass either outcome_id or accomplishment_id")
    if outcome_id is not None:
        sql = "SELECT * FROM evidence WHERE outcome_id=? ORDER BY id"
        args: tuple[Any, ...] = (outcome_id,)
    else:
        sql = """SELECT e.* FROM evidence e
                 JOIN outcome o ON o.id = e.outcome_id
                 WHERE o.accomplishment_id=? ORDER BY e.id"""
        args = (accomplishment_id,)
    with _conn(db_path) as conn:
        return list(conn.execute(sql, args).fetchall())


VALID_EVIDENCE_SOURCES = ("self_reported", "manager_quoted", "system_exported", "public")


def insert_evidence(
    *,
    outcome_id: int,
    kind: str,
    source: str,
    url_or_path: str | None = None,
    notes: str | None = None,
    asof_date: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    if source not in VALID_EVIDENCE_SOURCES:
        raise ValueError(
            f"Invalid evidence source '{source}'. "
            f"Must be one of {VALID_EVIDENCE_SOURCES}"
        )
    with _conn(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO evidence (
                  outcome_id, kind, source, url_or_path, notes, asof_date
               ) VALUES (?, ?, ?, ?, ?, ?)""",
            (outcome_id, kind, source, url_or_path, notes, asof_date),
        )
        conn.commit()
        return cur.lastrowid


def upgrade_evidence(
    evidence_id: int,
    *,
    source: str | None = None,
    url_or_path: str | None = None,
    notes: str | None = None,
    db_path: str | Path | None = None,
) -> None:
    """Sean uses this via /coin add-evidence to promote self_reported → public."""
    if source and source not in VALID_EVIDENCE_SOURCES:
        raise ValueError(f"Invalid source. Must be one of {VALID_EVIDENCE_SOURCES}")
    sets = []
    args: list[Any] = []
    if source is not None:
        sets.append("source=?")
        args.append(source)
    if url_or_path is not None:
        sets.append("url_or_path=?")
        args.append(url_or_path)
    if notes is not None:
        sets.append("notes=?")
        args.append(notes)
    if not sets:
        return
    args.append(evidence_id)
    with _conn(db_path) as conn:
        conn.execute(f"UPDATE evidence SET {', '.join(sets)} WHERE id=?", args)
        conn.commit()


# ── Skill / tagging queries ─────────────────────────────────────────────

def get_skill_by_slug(slug: str, *, db_path: str | Path | None = None) -> sqlite3.Row | None:
    with _conn(db_path) as conn:
        return conn.execute("SELECT * FROM skill WHERE slug=?", (slug,)).fetchone()


def search_skills(
    query: str,
    *,
    limit: int = 20,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    """Case-insensitive substring search over name + slug."""
    q = f"%{query.lower()}%"
    with _conn(db_path) as conn:
        return list(conn.execute(
            """SELECT * FROM skill
               WHERE LOWER(name) LIKE ? OR LOWER(slug) LIKE ?
               ORDER BY length(name), name LIMIT ?""",
            (q, q, limit),
        ).fetchall())


def list_skills_for_accomplishment(
    accomplishment_id: int,
    *,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    with _conn(db_path) as conn:
        return list(conn.execute(
            """SELECT s.*, asx.weight
               FROM skill s
               JOIN accomplishment_skill asx ON asx.skill_id = s.id
               WHERE asx.accomplishment_id = ?
               ORDER BY asx.weight DESC, s.name""",
            (accomplishment_id,),
        ).fetchall())


def tag_skill(
    *,
    accomplishment_id: int,
    skill_slug: str,
    weight: int = 5,
    db_path: str | Path | None = None,
) -> bool:
    """Tag an accomplishment with a skill (idempotent). Returns True if created/updated."""
    if not (1 <= weight <= 10):
        raise ValueError("weight must be 1..10")
    with _conn(db_path) as conn:
        skill = conn.execute("SELECT id FROM skill WHERE slug=?", (skill_slug,)).fetchone()
        if not skill:
            return False
        conn.execute(
            """INSERT INTO accomplishment_skill (accomplishment_id, skill_id, weight)
               VALUES (?, ?, ?)
               ON CONFLICT(accomplishment_id, skill_id)
               DO UPDATE SET weight = excluded.weight""",
            (accomplishment_id, skill["id"], weight),
        )
        conn.commit()
        return True


# ── Lane relevance queries ───────────────────────────────────────────────

def set_lane_relevance(
    *,
    accomplishment_id: int,
    lane_slug: str,
    relevance_score: int,
    manual_pin: bool = False,
    db_path: str | Path | None = None,
) -> bool:
    if not (0 <= relevance_score <= 100):
        raise ValueError("relevance_score must be 0..100")
    with _conn(db_path) as conn:
        lane = conn.execute("SELECT id FROM lane WHERE slug=?", (lane_slug,)).fetchone()
        if not lane:
            return False
        conn.execute(
            """INSERT INTO accomplishment_lane (
                  accomplishment_id, lane_id, relevance_score, manual_pin
               ) VALUES (?, ?, ?, ?)
               ON CONFLICT(accomplishment_id, lane_id) DO UPDATE SET
                  relevance_score = excluded.relevance_score,
                  manual_pin = excluded.manual_pin""",
            (accomplishment_id, lane["id"], relevance_score, 1 if manual_pin else 0),
        )
        conn.commit()
        return True


# ── Bullet variant cache ────────────────────────────────────────────────

VALID_LENGTH_BUCKETS = ("short", "medium", "long")


def upsert_bullet_variant(
    *,
    accomplishment_id: int,
    lane_slug: str,
    length_bucket: str,
    text: str,
    tone: str | None = None,
    last_audit_pass: bool = False,
    db_path: str | Path | None = None,
) -> int:
    if length_bucket not in VALID_LENGTH_BUCKETS:
        raise ValueError(f"length_bucket must be one of {VALID_LENGTH_BUCKETS}")
    with _conn(db_path) as conn:
        lane = conn.execute("SELECT id FROM lane WHERE slug=?", (lane_slug,)).fetchone()
        if not lane:
            raise ValueError(f"Unknown lane: {lane_slug}")
        # SQLite UNIQUE INDEX with COALESCE handles NULL tone correctly.
        existing = conn.execute(
            """SELECT id FROM bullet_variant
               WHERE accomplishment_id=? AND lane_id=? AND length_bucket=?
                 AND COALESCE(tone, '') = COALESCE(?, '')""",
            (accomplishment_id, lane["id"], length_bucket, tone),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE bullet_variant SET
                      text=?, last_audit_pass=?, generated_at=datetime('now')
                   WHERE id=?""",
                (text, 1 if last_audit_pass else 0, existing["id"]),
            )
            conn.commit()
            return existing["id"]
        cur = conn.execute(
            """INSERT INTO bullet_variant (
                  accomplishment_id, lane_id, length_bucket, tone, text,
                  last_audit_pass, used_in_role_ids
               ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (accomplishment_id, lane["id"], length_bucket, tone, text,
             1 if last_audit_pass else 0, json.dumps([])),
        )
        conn.commit()
        return cur.lastrowid


def get_bullet_variants(
    *,
    accomplishment_id: int | None = None,
    lane_slug: str | None = None,
    length_bucket: str | None = None,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    sql = "SELECT bv.*, l.slug AS lane_slug FROM bullet_variant bv JOIN lane l ON l.id = bv.lane_id WHERE 1=1"
    args: list[Any] = []
    if accomplishment_id is not None:
        sql += " AND bv.accomplishment_id=?"
        args.append(accomplishment_id)
    if lane_slug:
        sql += " AND l.slug=?"
        args.append(lane_slug)
    if length_bucket:
        sql += " AND bv.length_bucket=?"
        args.append(length_bucket)
    sql += " ORDER BY bv.id"
    with _conn(db_path) as conn:
        return list(conn.execute(sql, args).fetchall())


def mark_variant_used(
    *,
    variant_id: int,
    role_id: int,
    db_path: str | Path | None = None,
) -> None:
    """Append role_id to the JSON array used_in_role_ids for trend tracking."""
    with _conn(db_path) as conn:
        row = conn.execute(
            "SELECT used_in_role_ids FROM bullet_variant WHERE id=?", (variant_id,)
        ).fetchone()
        if not row:
            return
        used = json.loads(row["used_in_role_ids"] or "[]")
        if role_id not in used:
            used.append(role_id)
        conn.execute(
            "UPDATE bullet_variant SET used_in_role_ids=? WHERE id=?",
            (json.dumps(used), variant_id),
        )
        conn.commit()


# ── JD keyword writes ───────────────────────────────────────────────────

VALID_TERM_KINDS = ("must_have", "nice_to_have", "industry", "tool")


def upsert_jd_keyword(
    *,
    role_id: int,
    term: str,
    term_kind: str = "must_have",
    importance: int = 5,
    lightcast_id: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    if term_kind not in VALID_TERM_KINDS:
        raise ValueError(f"term_kind must be one of {VALID_TERM_KINDS}")
    if not (1 <= importance <= 10):
        raise ValueError("importance must be 1..10")
    with _conn(db_path) as conn:
        existing = conn.execute(
            "SELECT id FROM jd_keyword WHERE role_id=? AND term=?",
            (role_id, term),
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE jd_keyword SET
                      term_kind=?, importance=?, lightcast_id=COALESCE(?, lightcast_id)
                   WHERE id=?""",
                (term_kind, importance, lightcast_id, existing["id"]),
            )
            conn.commit()
            return existing["id"]
        cur = conn.execute(
            """INSERT INTO jd_keyword (role_id, term, term_kind, importance, lightcast_id)
               VALUES (?, ?, ?, ?, ?)""",
            (role_id, term, term_kind, importance, lightcast_id),
        )
        conn.commit()
        return cur.lastrowid


def list_jd_keywords(
    role_id: int,
    *,
    term_kind: str | None = None,
    min_importance: int = 1,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM jd_keyword WHERE role_id=? AND importance >= ?"
    args: list[Any] = [role_id, min_importance]
    if term_kind:
        sql += " AND term_kind=?"
        args.append(term_kind)
    sql += " ORDER BY importance DESC, term"
    with _conn(db_path) as conn:
        return list(conn.execute(sql, args).fetchall())


# ── Render artifact writes ──────────────────────────────────────────────

VALID_VARIANT_KINDS = ("designed", "ats", "weasy")


def insert_render_artifact(
    *,
    role_id: int,
    theme: str,
    variant_kind: str,
    pdf_path: str,
    ats_score: int | None = None,
    keyword_overlap_pct: float | None = None,
    buzzword_density_pct: float | None = None,
    truthfulness_pass: bool | None = None,
    page_count: int | None = None,
    notes: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    if variant_kind not in VALID_VARIANT_KINDS:
        raise ValueError(f"variant_kind must be one of {VALID_VARIANT_KINDS}")
    with _conn(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO render_artifact (
                  role_id, theme, variant_kind, pdf_path,
                  ats_score, keyword_overlap_pct, buzzword_density_pct,
                  truthfulness_pass, page_count, notes
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (role_id, theme, variant_kind, pdf_path,
             ats_score, keyword_overlap_pct, buzzword_density_pct,
             None if truthfulness_pass is None else (1 if truthfulness_pass else 0),
             page_count, notes),
        )
        conn.commit()
        return cur.lastrowid


def list_render_artifacts(
    role_id: int,
    *,
    db_path: str | Path | None = None,
) -> list[sqlite3.Row]:
    with _conn(db_path) as conn:
        return list(conn.execute(
            "SELECT * FROM render_artifact WHERE role_id=? ORDER BY rendered_at DESC, id DESC",
            (role_id,),
        ).fetchall())


# ── Composite reads (used by tailor/audit/score_panel) ──────────────────

def assemble_for_lane(
    lane_slug: str,
    *,
    min_relevance: int = 60,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Returns a structured payload — the input for the ranker prompt.

    Shape per row:
        {
            "accomplishment": {...},
            "outcomes": [...],
            "evidence": [...],
            "skills": [...],
            "lane_relevance": int,
        }

    Strict no-bullet-text — bullets live in raw_text_source plus
    bullet_variant rows. The ranker's input is fact + provenance, not
    pre-rendered prose.
    """
    out: list[dict[str, Any]] = []
    accs = list_accomplishments_for_lane(
        lane_slug, min_relevance=min_relevance, db_path=db_path
    )
    for a in accs:
        a_id = a["id"]
        out.append({
            "accomplishment": dict(a),
            "outcomes": [dict(o) for o in list_outcomes(a_id, db_path=db_path)],
            "evidence": [dict(e) for e in list_evidence(accomplishment_id=a_id, db_path=db_path)],
            "skills": [dict(s) for s in list_skills_for_accomplishment(a_id, db_path=db_path)],
            "lane_relevance": int(a["relevance_score"]),
        })
    return out
