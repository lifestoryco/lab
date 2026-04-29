"""Supabase backend for the COIN pipeline.

Mirrors the public API of pipeline.py (the legacy SQLite backend). The
selector at the top of pipeline.py picks this module when SUPABASE_URL
and SUPABASE_SERVICE_ROLE_KEY are both set in the environment.

Operates with the service-role key — RLS is bypassed because the
local CLI is trusted code with full DB credentials anyway. Every write
that mutates state also appends a row to role_events so the weekly
improvement loop ('compare model to outcome') stays complete regardless
of whether the change came from the CLI or the web dashboard.

Design notes:
  - Two-step upsert (SELECT existing → merge in Python → upsert) instead
    of a Postgres function, to keep the migration small. Race window is
    Sean-vs-Sean which is ~zero risk for a single-user CLI.
  - jd_parsed is jsonb in Postgres; we accept dicts and JSON-strings
    transparently, returning dicts to callers.
  - Returned role rows mimic the SQLite shape (notably: fit_score is
    rewritten to the authoritative score so existing callers see no diff).

Required environment:
  SUPABASE_URL                 https://<ref>.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    long JWT, project setting → API
  COIN_USER_ID                 auth.users.id of the operator (uuid string)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from supabase import Client, create_client

STATUSES = [
    "discovered", "scored", "resume_generated", "applied", "responded",
    "contact", "interviewing", "offer", "rejected", "withdrawn", "no_apply", "closed",
]
TERMINAL_STATUSES = {"offer", "rejected", "withdrawn", "no_apply", "closed"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


_client: Client | None = None
_user_id: str | None = None


def _get() -> tuple[Client, str]:
    global _client, _user_id
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        uid = os.environ.get("COIN_USER_ID")
        if not (url and key and uid):
            raise RuntimeError(
                "Supabase backend selected but missing env vars. "
                "Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and COIN_USER_ID."
            )
        _client = create_client(url, key)
        _user_id = uid
    return _client, _user_id  # type: ignore[return-value]


def _normalize_role(row: dict) -> dict:
    """Adapt a Supabase row to the legacy SQLite-shaped dict.

    Promotes the authoritative score (stage_2 → stage_1 → fit_score) onto
    `fit_score` so callers don't need to know which stage produced it.
    """
    if not row:
        return row
    s2 = row.get("score_stage2")
    s1 = row.get("score_stage1")
    if s2 is not None:
        row["fit_score"] = s2
        row["_stage"] = "S2"
    elif s1 is not None:
        row["fit_score"] = s1
        row["_stage"] = "S1"
    else:
        row["_stage"] = "S1"
    # jd_parsed comes back as dict (jsonb); legacy callers expect either
    # string or dict — leave as dict, callers already handle both.
    return row


# ── init ────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """No-op — the schema is owned by the SQL migration in
    web/supabase/migrations/. Kept so callers that invoke `init_db()` at
    startup don't error."""
    return None


# ── upsert ──────────────────────────────────────────────────────────────────

def _existing_role_by_url(url: str) -> dict | None:
    sb, uid = _get()
    res = (
        sb.table("roles")
        .select("*")
        .eq("user_id", uid)
        .eq("url", url)
        .maybe_single()
        .execute()
    )
    return res.data if res and res.data else None


def upsert_role(role: dict) -> int:
    """Insert or merge a scraped role. Mirrors SQLite ON CONFLICT(url) DO UPDATE
    semantics, plus the out_of_band quarantine and Levels.fyi auto-impute."""
    sb, uid = _get()
    if not role.get("url"):
        raise ValueError("role.url required")

    now = _now()
    incoming = {
        "user_id":         uid,
        "url":             role.get("url"),
        "title":           role.get("title"),
        "company":         role.get("company"),
        "location":        role.get("location"),
        "remote":          bool(role.get("remote") or False),
        "lane":            role.get("lane"),
        "comp_min":        role.get("comp_min"),
        "comp_max":        role.get("comp_max"),
        "comp_source":     role.get("comp_source"),
        "comp_currency":   role.get("comp_currency") or "USD",
        "comp_confidence": role.get("comp_confidence"),
        "fit_score":       role.get("fit_score"),
        "source":          role.get("source"),
        "jd_raw":          role.get("jd_raw"),
        "posted_at":       role.get("posted_at"),
        "discovered_at":   now,
        "updated_at":      now,
    }

    existing = _existing_role_by_url(incoming["url"])
    if existing:
        # Merge with COALESCE-like semantics: incoming non-null overrides;
        # null leaves existing. Plus the two invariants from the SQLite
        # ON CONFLICT block:
        #   - out_of_band lane → fit_score stays 0
        #   - posted_at: never clobber non-null with null
        merged = {**existing}
        for k, v in incoming.items():
            if k in ("user_id", "url", "discovered_at"):
                continue
            if k == "remote":
                merged[k] = incoming[k]                    # always overwritten
                continue
            if v is not None:
                merged[k] = v
        if existing.get("lane") == "out_of_band":
            merged["fit_score"] = 0
        if incoming.get("posted_at") is None and existing.get("posted_at") is not None:
            merged["posted_at"] = existing["posted_at"]
        merged["updated_at"] = now
        merged.pop("id", None)
        sb.table("roles").update(merged).eq("id", existing["id"]).execute()
        role_id = int(existing["id"])
    else:
        # Drop None values for cleaner inserts.
        incoming_clean = {k: v for k, v in incoming.items() if v is not None}
        # `remote`/`comp_currency` defaults are handled by the column defaults.
        res = sb.table("roles").insert(incoming_clean).execute()
        role_id = int(res.data[0]["id"])

    # Levels.fyi auto-impute (parity with SQLite path).
    if role.get("comp_source") == "unverified" and role.get("company"):
        try:
            from careerops.levels import impute_comp
            imputed = impute_comp(role.get("company"), role.get("title"))
        except Exception as e:
            imputed = None
            print(f"[levels] impute_comp failed for {role.get('company')!r}: {e}")
        if imputed:
            note_suffix = (
                f"\n[imputed comp from Levels.fyi seed: "
                f"{imputed['level_matched']} @ confidence {imputed['confidence']}]"
            )
            existing_notes = (existing or {}).get("notes") or ""
            sb.table("roles").update({
                "comp_min":        imputed["comp_min"],
                "comp_max":        imputed["comp_max"],
                "comp_source":     imputed["comp_source"],
                "comp_confidence": imputed["confidence"],
                "notes":           existing_notes + note_suffix,
                "updated_at":      _now(),
            }).eq("id", role_id).execute()

    return role_id


def _role_id_by_url(url: str) -> int:
    r = _existing_role_by_url(url)
    return int(r["id"]) if r else 0


def upsert_roles(roles: list[dict]) -> list[int]:
    return [upsert_role(r) for r in roles]


# ── reads ───────────────────────────────────────────────────────────────────

def get_role(role_id: int) -> dict | None:
    sb, uid = _get()
    res = (
        sb.table("roles")
        .select("*")
        .eq("user_id", uid)
        .eq("id", role_id)
        .maybe_single()
        .execute()
    )
    return _normalize_role(res.data) if res and res.data else None


def list_roles(status: str | None = None, lane: str | None = None, limit: int = 50) -> list[dict]:
    sb, uid = _get()
    q = sb.table("roles").select("*").eq("user_id", uid)
    if status:
        q = q.eq("status", status)
    if lane:
        q = q.eq("lane", lane)
    # PostgREST can't ORDER BY a COALESCE expression; fetch a buffer and
    # sort in Python. Sean's pipeline is small (<10k rows in worst case)
    # so this is fine.
    rows = q.limit(min(limit * 4, 2000)).execute().data or []

    def rank(r: dict) -> float:
        return r.get("score_stage2") or r.get("score_stage1") or r.get("fit_score") or float("-inf")
    rows.sort(key=rank, reverse=True)
    return [_normalize_role(r) for r in rows[:limit]]


# ── role_events helper ──────────────────────────────────────────────────────

def _emit_event(role_id: int, event_type: str, payload: dict | None = None) -> None:
    sb, uid = _get()
    sb.table("role_events").insert({
        "role_id":    role_id,
        "user_id":    uid,
        "event_type": event_type,
        "payload":    payload or {},
    }).execute()


# ── mutations ───────────────────────────────────────────────────────────────

def update_status(role_id: int, status: str, note: str | None = None) -> None:
    if status not in STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of: {STATUSES}")
    sb, uid = _get()
    prev = get_role(role_id)
    updates: dict[str, Any] = {"status": status, "updated_at": _now()}
    if note:
        existing_notes = prev.get("notes") if prev else None
        appended = f"[{_today()} {status}] {note}"
        updates["notes"] = (existing_notes + "\n" if existing_notes else "") + appended
    sb.table("roles").update(updates).eq("user_id", uid).eq("id", role_id).execute()
    _emit_event(role_id, "status_change", {
        "from": prev.get("status") if prev else None, "to": status, "note": note,
    })


def update_fit_score(role_id: int, score: float) -> None:
    sb, uid = _get()
    prev = get_role(role_id)
    new_status = "scored" if (prev and prev.get("status") == "discovered") else None
    updates: dict[str, Any] = {"fit_score": score, "updated_at": _now()}
    if new_status:
        updates["status"] = new_status
    sb.table("roles").update(updates).eq("user_id", uid).eq("id", role_id).execute()


def update_jd_parsed(role_id: int, parsed: dict) -> None:
    sb, uid = _get()
    now = _now()
    updates: dict[str, Any] = {
        "jd_parsed":    parsed,
        "jd_parsed_at": now,
        "updated_at":   now,
    }
    sb.table("roles").update(updates).eq("user_id", uid).eq("id", role_id).execute()
    if parsed.get("comp_explicit") and parsed.get("comp_min"):
        sb.table("roles").update({
            "comp_min":    parsed["comp_min"],
            "comp_max":    parsed.get("comp_max"),
            "comp_source": "explicit",
            "updated_at":  _now(),
        }).eq("user_id", uid).eq("id", role_id).execute()


def update_lane(role_id: int, lane: str) -> None:
    sb, uid = _get()
    updates: dict[str, Any] = {"lane": lane, "updated_at": _now()}
    if lane == "out_of_band":
        updates["fit_score"] = 0
    sb.table("roles").update(updates).eq("user_id", uid).eq("id", role_id).execute()


def update_role_notes(role_id: int, note: str, append: bool = True) -> None:
    sb, uid = _get()
    if append:
        prev = get_role(role_id)
        existing_notes = (prev or {}).get("notes") or ""
        new_notes = (existing_notes + ("\n" if existing_notes else "")) + f"[{_today()}] {note}"
        sb.table("roles").update({
            "notes":      new_notes,
            "updated_at": _now(),
        }).eq("user_id", uid).eq("id", role_id).execute()
    else:
        sb.table("roles").update({
            "notes":      note,
            "updated_at": _now(),
        }).eq("user_id", uid).eq("id", role_id).execute()
    _emit_event(role_id, "note_added", {"text": note})


def update_jd_raw(role_id: int, jd: str) -> None:
    sb, uid = _get()
    sb.table("roles").update({
        "jd_raw":     jd,
        "updated_at": _now(),
    }).eq("user_id", uid).eq("id", role_id).execute()


def update_score_stage1(role_id: int, score: float) -> None:
    sb, uid = _get()
    prev = get_role(role_id)
    updates: dict[str, Any] = {
        "score_stage1": score,
        "fit_score":    score,
        "score_stage":  1,
        "updated_at":   _now(),
    }
    if prev and prev.get("status") == "discovered":
        updates["status"] = "scored"
    sb.table("roles").update(updates).eq("user_id", uid).eq("id", role_id).execute()


def update_score_stage2(
    role_id: int,
    score: float,
    *,
    breakdown: dict | None = None,
) -> None:
    sb, uid = _get()
    updates: dict[str, Any] = {
        "score_stage2": score,
        "fit_score":    score,
        "score_stage":  2,
        "updated_at":   _now(),
    }
    if breakdown is not None:
        updates["jd_parsed"] = breakdown
    sb.table("roles").update(updates).eq("user_id", uid).eq("id", role_id).execute()


def get_top_n_for_deep_score(n: int = 15) -> list[dict]:
    """Top N stage-1-scored roles that haven't been deep-scored yet."""
    sb, uid = _get()
    rows = (
        sb.table("roles")
        .select("*")
        .eq("user_id", uid)
        .is_("score_stage2", None)
        .not_.is_("score_stage1", None)
        .order("score_stage1", desc=True)
        .limit(n)
        .execute()
    ).data or []
    return [_normalize_role(r) for r in rows]


# ── offers ──────────────────────────────────────────────────────────────────

def insert_offer(offer: dict) -> int:
    sb, uid = _get()
    payload = {**offer, "user_id": uid}
    res = sb.table("offers").insert(payload).execute()
    return int(res.data[0]["id"])


def list_offers(status: str | None = "active") -> list[dict]:
    sb, uid = _get()
    q = sb.table("offers").select("*").eq("user_id", uid)
    if status:
        q = q.eq("status", status)
    return q.order("received_at", desc=True).execute().data or []


def insert_market_anchor(
    company: str,
    title: str,
    base_salary: int,
    *,
    rsu_total_value: int = 0,
    annual_bonus_target_pct: float = 0.0,
    state_tax: str = "UT",
    source: str = "Levels.fyi",
    notes: str | None = None,
) -> int:
    return insert_offer({
        "company": company,
        "title": title,
        "received_at": _today(),
        "base_salary": base_salary,
        "rsu_total_value": rsu_total_value,
        "annual_bonus_target_pct": annual_bonus_target_pct,
        "state_tax": state_tax,
        "growth_signal": source,
        "notes": notes,
        "status": "market_anchor",
    })


def list_market_anchors() -> list[dict]:
    return list_offers(status="market_anchor")


# ── outreach ────────────────────────────────────────────────────────────────

def tag_outreach_role(
    outreach_id: int,
    role_id: int,
    *,
    contact_role: str | None = None,
) -> None:
    sb, uid = _get()
    updates: dict[str, Any] = {"target_role_id": role_id}
    if contact_role:
        updates["contact_role"] = contact_role
    sb.table("outreach").update(updates).eq("user_id", uid).eq("id", outreach_id).execute()


def find_hiring_manager_for_role(role_id: int) -> dict | None:
    sb, uid = _get()
    role = get_role(role_id)
    if not role or not role.get("company"):
        return None
    company = role["company"].strip().lower()
    res = (
        sb.table("connections")
        .select("*")
        .eq("user_id", uid)
        .ilike("company_normalized", f"%{company}%")
        .order("seniority", desc=True)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


# ── summary / dashboard ─────────────────────────────────────────────────────

def summary() -> dict:
    sb, uid = _get()
    rows = sb.table("roles").select("status, fit_score, comp_min, comp_max").eq("user_id", uid).execute().data or []
    counts: dict[str, int] = {}
    for r in rows:
        counts[r.get("status") or "unknown"] = counts.get(r.get("status") or "unknown", 0) + 1
    active = [r for r in rows if (r.get("status") or "") not in TERMINAL_STATUSES]
    avg_fit = (
        sum((r.get("fit_score") or 0) for r in active) / len(active)
        if active else 0
    )
    return {
        "counts":   counts,
        "total":    len(rows),
        "active":   len(active),
        "avg_fit":  round(avg_fit, 1),
    }


def dashboard() -> None:
    """Stub. The web dashboard at /lab/coin is the canonical view in the
    Supabase era; the CLI Rich dashboard reading SQLite directly is gone.
    Keeping this function so callers don't ImportError."""
    s = summary()
    print(f"COIN — {s['total']} roles ({s['active']} active), avg fit {s['avg_fit']:.1f}")
    for k, v in sorted(s["counts"].items(), key=lambda kv: -kv[1]):
        print(f"  {k:<18} {v}")
