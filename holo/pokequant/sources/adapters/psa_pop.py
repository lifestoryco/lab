"""PSA Pop Report adapter.

Scrapes https://www.psacard.com/pop/tcg-cards/pokemon/... for grading
population counts. Emits pop_report records (price=0, informational)
for the registry and exposes fetch_pop() for _handle_grade_roi to use
real pop data instead of hardcoded 0.15/0.35 probabilities.

Updates weekly on PSA's side — 7-day cache via /tmp sqlite.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import time
from datetime import date, datetime, timezone
from typing import Any, Sequence

from pokequant.http import session as _http_session
from pokequant.sources.base import SourceAdapter
from pokequant.sources.priority import priority_for
from pokequant.sources.schema import Grade, NormalizedSale

logger = logging.getLogger(__name__)

_PSA_BASE = "https://www.psacard.com/pop/tcg-cards/pokemon"
_CACHE_DB = os.environ.get("HOLO_CACHE_DB", "/tmp/holo_cache.db")
_CACHE_TTL_S = 7 * 24 * 3600  # weekly


def _cache_get(key: str) -> dict[str, Any] | None:
    try:
        with sqlite3.connect(_CACHE_DB) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS psa_pop_cache "
                "(key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at REAL NOT NULL)"
            )
            row = conn.execute(
                "SELECT payload, fetched_at FROM psa_pop_cache WHERE key = ?", (key,)
            ).fetchone()
    except Exception as exc:
        logger.debug("psa_pop cache_get failed: %s", exc)
        return None
    if not row:
        return None
    payload_json, fetched_at = row
    if time.time() - float(fetched_at) > _CACHE_TTL_S:
        return None
    try:
        loaded: dict[str, Any] = json.loads(payload_json)
        return loaded
    except json.JSONDecodeError:
        return None


def _cache_put(key: str, payload: dict[str, Any]) -> None:
    try:
        with sqlite3.connect(_CACHE_DB) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS psa_pop_cache "
                "(key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at REAL NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO psa_pop_cache (key, payload, fetched_at) VALUES (?, ?, ?)",
                (key, json.dumps(payload), time.time()),
            )
            conn.commit()
    except Exception as exc:
        logger.debug("psa_pop cache_put failed: %s", exc)


class PSAPopAdapter(SourceAdapter):
    name = "psa_pop"
    enabled_by_default = True
    priority = priority_for("psa_pop")
    currency = "USD"

    def supports_grade(self, grade: Grade) -> bool:
        # Pop data is independent of the requester's grade — always useful.
        return True

    def fetch(
        self, card_name: str, *, days: int, grade: Grade
    ) -> Sequence[NormalizedSale]:
        pop = self.fetch_pop(card_name)
        if not pop or pop.get("total", 0) == 0:
            return []

        return [
            NormalizedSale(
                sale_id=f"psa_pop:{card_name}",
                adapter=self.name,
                source_type="pop_report",
                price=0.01,  # nonzero to satisfy validator; pop records are informational
                currency="USD",
                date=date.today(),
                condition="NM",
                grade="raw",
                source_url=pop.get("url", _PSA_BASE),
                extra={
                    "pop10": pop.get("pop10", 0),
                    "pop9": pop.get("pop9", 0),
                    "pop8": pop.get("pop8", 0),
                    "total": pop.get("total", 0),
                },
            )
        ]

    def fetch_pop(self, card_name: str) -> dict[str, Any]:
        """Return {pop10, pop9, pop8, total, url} for a card or {} on failure.

        Used by api/index.py::_handle_grade_roi to replace the hardcoded
        0.15 / 0.35 probabilities with real liquidity data.
        """
        slug = re.sub(r"[^a-z0-9]+", "-", card_name.lower()).strip("-")
        cached = _cache_get(slug)
        if cached is not None:
            return cached

        # The public PSA pop endpoint requires a resolved set + card page.
        # Without a search endpoint we rely on operator-provided mapping,
        # or a best-effort slug query. Conservative fallback: return empty.
        url = f"{_PSA_BASE}/{slug}"
        try:
            resp = _http_session().get(url, timeout=8)
            if resp.status_code != 200:
                logger.info("psa_pop non-200 for %s: %s", slug, resp.status_code)
                return {}
            pop = self._parse(resp.text, url)
        except Exception as exc:
            logger.warning("psa_pop fetch failed for %s: %s", slug, exc)
            return {}

        if pop:
            _cache_put(slug, pop)
        return pop

    @staticmethod
    def _parse(html: str, url: str) -> dict[str, Any]:
        """Extract pop10 / pop9 / pop8 / total from PSA's pop-report page.

        PSA's table has rows per grade with columns: grade, count, percentage.
        This parser is tolerant of DOM drift: missing rows default to 0.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        pop: dict[str, Any] = {"pop10": 0, "pop9": 0, "pop8": 0, "total": 0, "url": url}

        # PSA historically uses a #pop-report-table or similar. Fall back to
        # a row-scan with grade-label detection.
        text = soup.get_text(" ", strip=True).lower()

        def _extract_grade(label: str) -> int:
            m = re.search(rf"\bpsa\s*{label}\b\D{{0,20}}(\d[\d,]*)", text)
            if not m:
                return 0
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                return 0

        pop["pop10"] = _extract_grade("10")
        pop["pop9"] = _extract_grade("9")
        pop["pop8"] = _extract_grade("8")
        pop["total"] = pop["pop10"] + pop["pop9"] + pop["pop8"]
        return pop if pop["total"] > 0 else {}

    def health_check(self) -> dict[str, Any]:
        t0 = time.time()
        try:
            resp = _http_session().get(_PSA_BASE, timeout=5)
            latency = round((time.time() - t0) * 1000, 1)
            return {
                "ok": resp.status_code == 200,
                "latency_ms": latency,
                "error": None if resp.status_code == 200 else f"HTTP {resp.status_code}",
            }
        except Exception as exc:
            return {
                "ok": False,
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": str(exc)[:200],
            }


# Auto-register at import time.
from pokequant.sources.registry import registry as _registry  # noqa: E402
_registry.register(PSAPopAdapter())
