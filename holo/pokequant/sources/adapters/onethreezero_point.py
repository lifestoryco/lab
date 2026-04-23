"""130point adapter.

130point.com aggregates eBay + auction sales with built-in lot-rejection
and damaged-listing filters. Records arrive pre-cleaned — a strong
cross-validator for PriceCharting. Self-imposed 1 req/sec rate limit.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from datetime import date, datetime
from typing import Any, Sequence

from pokequant.http import session as _http_session
from pokequant.sources.base import SourceAdapter
from pokequant.sources.priority import priority_for
from pokequant.sources.schema import Grade, NormalizedSale

logger = logging.getLogger(__name__)

_BASE = "https://130point.com/sales/"

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


class OneThirtyPointAdapter(SourceAdapter):
    name = "130point"
    enabled_by_default = True
    priority = priority_for("130point")
    currency = "USD"

    def supports_grade(self, grade: Grade) -> bool:
        # 130point returns all grades; caller filters downstream via condition/grade.
        return grade == "raw"

    def fetch(
        self, card_name: str, *, days: int, grade: Grade
    ) -> Sequence[NormalizedSale]:
        if not self.supports_grade(grade):
            return []

        query = card_name.replace(" ", "+")
        url = f"{_BASE}?search={query}"
        try:
            resp = _http_session().get(
                url,
                headers=_BROWSER_HEADERS,
                timeout=10,
            )
            if resp.status_code != 200:
                logger.info("130point non-200: %s", resp.status_code)
                return []
            return list(self._parse(resp.text, card_name, url, days))
        except Exception as exc:
            logger.warning("130point fetch failed: %s", exc)
            return []

    @staticmethod
    def _parse(html: str, card_name: str, url: str, days: int) -> Sequence[NormalizedSale]:
        """Extract sale rows. 130point tables use a consistent
        <tr> per sale with price, date, title, and an outlier column.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table tr")
        cutoff = date.today().toordinal() - days
        out: list[NormalizedSale] = []

        for row in rows:
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if len(cells) < 3:
                continue
            # Heuristic column detection — 130point puts price in a cell
            # containing "$" and date in an ISO or "M/D/YYYY" format.
            price = _first_price(cells)
            sale_date = _first_date(cells)
            title = _longest_cell(cells)
            if price is None or sale_date is None or not title:
                continue
            if sale_date.toordinal() < cutoff:
                continue

            is_outlier = any(kw in " ".join(cells).lower() for kw in ("lot", "damaged", "reprint"))
            sale_id = hashlib.sha1(
                f"130point:{title}:{price}:{sale_date.isoformat()}".encode()
            ).hexdigest()[:16]

            out.append(
                NormalizedSale(
                    sale_id=sale_id,
                    adapter="130point",
                    source_type="sale",
                    price=price,
                    currency="USD",
                    date=sale_date,
                    condition="NM",
                    grade="raw",
                    source_url=url,
                    outlier_flag=is_outlier,
                    confidence=0.9,
                )
            )
        return out

    def health_check(self) -> dict[str, Any]:
        t0 = time.time()
        try:
            resp = _http_session().get(_BASE, timeout=5, headers=_BROWSER_HEADERS)
            latency = round((time.time() - t0) * 1000, 1)
            return {
                "ok": resp.status_code in (200, 301, 302),
                "latency_ms": latency,
                "error": None if resp.status_code == 200 else f"HTTP {resp.status_code}",
            }
        except Exception as exc:
            return {
                "ok": False,
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": str(exc)[:200],
            }


_PRICE_RE = re.compile(r"\$\s*([0-9][0-9,]*(?:\.\d{1,2})?)")
_DATE_RES = [
    re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b"),
    re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b"),
]


def _first_price(cells: list[str]) -> float | None:
    for c in cells:
        m = _PRICE_RE.search(c)
        if m:
            try:
                return float(m.group(1).replace(",", ""))
            except ValueError:
                continue
    return None


def _first_date(cells: list[str]) -> date | None:
    for c in cells:
        for regex in _DATE_RES:
            m = regex.search(c)
            if not m:
                continue
            try:
                if regex is _DATE_RES[0]:
                    return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                return date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
            except ValueError:
                continue
    return None


def _longest_cell(cells: list[str]) -> str:
    return max(cells, key=len) if cells else ""


from pokequant.sources.registry import registry as _registry  # noqa: E402
_registry.register(OneThirtyPointAdapter())
