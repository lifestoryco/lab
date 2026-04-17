"""Level-2 persistent cache backed by Supabase Postgres (via PostgREST).

Complements the /tmp sqlite L1 cache with durable cross-instance storage
so that popular cards don't re-scrape PriceCharting on every Vercel cold
start. Also builds a proprietary time-series of scraped sales as a
long-term data moat.

═══════════════════════════════════════════════════════════════════════════
Design
═══════════════════════════════════════════════════════════════════════════

• **Feature-gated.** If `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY`
  env vars are unset, every function in this module is a no-op and
  `fetch_sales()` behaves exactly as before (L1 + live scrape only).
  The module is safe to deploy before Supabase is configured.

• **Schema-isolated.** All tables live in the `holo` schema, NOT
  `public`. Communicates with PostgREST via the Accept-Profile /
  Content-Profile headers. Requires `holo` to be added to exposed
  schemas in dashboard → API settings.

• **Graceful degradation.** Every Supabase call has a short timeout
  (3-4s) and is wrapped in try/except. A Supabase outage can NEVER
  kill a user request — the scraper falls through to live fetch as
  if L2 didn't exist.

• **Fire-and-forget writes.** `put_sales` never raises. Failures are
  logged at DEBUG only; the request path is already back to the user
  by the time we care whether the write landed.

• **Idempotent.** Sale rows are keyed by a deterministic sha1 of
  (source, source_url, price_cents, sale_date). Re-inserting the same
  underlying sale is a no-op (`Prefer: resolution=ignore-duplicates`).

═══════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ─── Config ────────────────────────────────────────────────────────────────
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "").rstrip("/")
# Server-only. NEVER prefix with NEXT_PUBLIC_, NEVER commit.
SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
# Legacy env name fallback — if you set SUPABASE_SERVICE_KEY we'll pick it up too.
if not SUPABASE_SERVICE_ROLE_KEY:
    SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

_ENABLED: bool = bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)

# Dedicated PostgREST schema. Matches db/migrations/001_holo_sales_cache.sql.
_SCHEMA: str = "holo"

# Supabase calls must never block the request path. Keep these tight.
_READ_TIMEOUT: float = 3.0
_WRITE_TIMEOUT: float = 4.0

# Trust L2 data for this long before re-scraping. Matches L1 TTL.
_L2_FRESH_HOURS: int = 24

# Reuse HTTP connections; Vercel keeps the interpreter warm within an invocation.
_session: requests.Session | None = None


def is_enabled() -> bool:
    """True when both SUPABASE_URL and a service-role key are set."""
    return _ENABLED


def _sess() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "apikey": SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        })
        _session = s
    return _session


def _sale_id(source: str, source_url: str | None, price_cents: int, sale_date: str) -> str:
    """Deterministic dedup key. Same sale scraped twice → same id → upsert no-op."""
    h = hashlib.sha1()
    h.update(f"{source}|{source_url or ''}|{price_cents}|{sale_date}".encode("utf-8"))
    return h.hexdigest()[:32]


# ─── Read path ─────────────────────────────────────────────────────────────

def get_recent_sales(card_slug: str, grade: str, days: int) -> list[dict[str, Any]] | None:
    """Return L2 sales for (card_slug, grade, last `days` days) if we have a
    fresh scrape on record, else None. Never raises.

    Returns None on:
      • Module disabled (env vars unset)
      • No scrape_runs row for (slug, grade, days) — never scraped before
      • Last scrape was > _L2_FRESH_HOURS ago — data considered stale
      • Supabase unreachable, slow, or errored (timeout or non-200)
    """
    if not _ENABLED:
        return None

    # 1. Freshness gate — did we do a live scrape recently?
    try:
        r = _sess().get(
            f"{SUPABASE_URL}/rest/v1/scrape_runs",
            headers={"Accept-Profile": _SCHEMA},
            params={
                "card_slug": f"eq.{card_slug}",
                "grade": f"eq.{grade}",
                "days": f"eq.{days}",
                "select": "last_fetched_at,sales_count",
                "limit": "1",
            },
            timeout=_READ_TIMEOUT,
        )
        if r.status_code != 200:
            logger.debug("supabase scrape_runs read %d for %s", r.status_code, card_slug)
            return None
        rows = r.json() or []
        if not rows:
            return None
        last_iso = rows[0].get("last_fetched_at")
        if not last_iso:
            return None
        # Postgres timestamptz serialises as "2026-04-17T22:10:00.123456+00:00"
        # (Python 3.11+ fromisoformat handles the offset natively).
        try:
            last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
        except ValueError:
            return None
        age_h = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600.0
        if age_h > _L2_FRESH_HOURS:
            logger.info(
                "supabase L2 stale for %s (%s, %dd): last scraped %.1fh ago",
                card_slug, grade, days, age_h,
            )
            return None
    except requests.RequestException as exc:
        logger.debug("supabase freshness check failed: %s", exc)
        return None

    # 2. Fetch the actual sales rows for the window.
    try:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        r = _sess().get(
            f"{SUPABASE_URL}/rest/v1/sales_cache",
            headers={"Accept-Profile": _SCHEMA},
            params={
                "card_slug": f"eq.{card_slug}",
                "grade": f"eq.{grade}",
                "sale_date": f"gte.{cutoff}",
                "select": "sale_id,source,source_url,sale_date,price_cents,title",
                "order": "sale_date.desc",
                "limit": "1000",
            },
            timeout=_READ_TIMEOUT,
        )
        if r.status_code != 200:
            logger.debug("supabase sales_cache read %d for %s", r.status_code, card_slug)
            return None
        rows = r.json() or []
        if not rows:
            return None
        # Reshape to the scraper's canonical wire format: price in dollars.
        sales = [{
            "sale_id": row["sale_id"],
            "source": row.get("source") or "",
            "source_url": row.get("source_url") or "",
            "date": row["sale_date"],
            "price": (row.get("price_cents") or 0) / 100.0,
            "title": row.get("title") or "",
            "grade": grade,
        } for row in rows]
        logger.info(
            "supabase L2 HIT for %s (%s, %dd) — %d sales.",
            card_slug, grade, days, len(sales),
        )
        return sales
    except requests.RequestException as exc:
        logger.debug("supabase sales fetch failed: %s", exc)
        return None


# ─── Write path ────────────────────────────────────────────────────────────

def put_sales(
    card_slug: str,
    grade: str,
    days: int,
    sales: list[dict[str, Any]],
) -> None:
    """Fire-and-forget write-through: push scraped sales into L2 + record
    a fresh scrape_runs row. Never raises, never blocks on failure.
    """
    if not _ENABLED or not sales:
        return

    rows: list[dict[str, Any]] = []
    for s in sales:
        try:
            price = float(s.get("price", 0) or 0)
            if price <= 0:
                continue
            price_cents = int(round(price * 100))
            sale_date = str(s.get("date") or "").strip()
            if not sale_date:
                continue
            source = str(s.get("source") or "unknown")
            source_url = s.get("source_url") or None
            sid = s.get("sale_id") or _sale_id(source, source_url, price_cents, sale_date)
            rows.append({
                "sale_id": sid,
                "card_slug": card_slug,
                "grade": grade,
                "source": source,
                "source_url": source_url,
                "sale_date": sale_date,
                "price_cents": price_cents,
                "title": (s.get("title") or "")[:500] or None,
            })
        except (TypeError, ValueError):
            # Malformed row — skip silently, don't poison the batch.
            continue

    if not rows:
        return

    # 1. Bulk-insert sales; duplicates detected on sale_id PK and ignored.
    try:
        r = _sess().post(
            f"{SUPABASE_URL}/rest/v1/sales_cache",
            headers={
                "Content-Type": "application/json",
                "Content-Profile": _SCHEMA,
                "Prefer": "resolution=ignore-duplicates,return=minimal",
            },
            data=json.dumps(rows),
            timeout=_WRITE_TIMEOUT,
        )
        if r.status_code >= 400:
            logger.debug("supabase sales_cache write %d: %s", r.status_code, r.text[:200])
    except requests.RequestException as exc:
        logger.debug("supabase sales_cache write failed: %s", exc)

    # 2. Upsert the freshness record (composite PK merge).
    try:
        r = _sess().post(
            f"{SUPABASE_URL}/rest/v1/scrape_runs",
            headers={
                "Content-Type": "application/json",
                "Content-Profile": _SCHEMA,
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            data=json.dumps({
                "card_slug": card_slug,
                "grade": grade,
                "days": days,
                "last_fetched_at": datetime.now(timezone.utc).isoformat(),
                "sales_count": len(rows),
            }),
            timeout=_WRITE_TIMEOUT,
        )
        if r.status_code >= 400:
            logger.debug("supabase scrape_runs upsert %d: %s", r.status_code, r.text[:200])
    except requests.RequestException as exc:
        logger.debug("supabase scrape_runs upsert failed: %s", exc)
