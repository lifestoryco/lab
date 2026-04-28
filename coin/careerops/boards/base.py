"""Board scraper ABC + shared helpers.

Pattern adapted from santifer/career-ops scan.mjs (MIT).
"""
from __future__ import annotations

import re
import time
from abc import ABC, abstractmethod
from typing import Optional

import httpx

from careerops.compensation import parse_comp_string

REMOTE_PATTERN = re.compile(r"\bremote|anywhere|distributed\b", re.I)

# Loose USD-range regex used as fallback against JD prose.
# Matches "$120,000 - $180,000", "$120K-$180K", "$120k to $180k", "120000-180000".
COMP_REGEX = re.compile(
    r"\$?\s*(\d{2,3})\s*[,]?(\d{3})?\s*[Kk]?\s*(?:-|–|to)\s*\$?\s*(\d{2,3})\s*[,]?(\d{3})?\s*[Kk]?",
)


def _strip_html(text: str) -> str:
    """Strip HTML tags. Cheap — full BeautifulSoup not needed for regex hunts."""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text)


def _regex_parse_comp(text: str) -> tuple[int | None, int | None]:
    """Apply COMP_REGEX to plain prose; delegate the parse to parse_comp_string."""
    if not text:
        return (None, None)
    m = COMP_REGEX.search(text)
    if not m:
        return (None, None)
    return parse_comp_string(m.group(0))


class BoardScraper(ABC):
    """Base class for public job-board API scrapers."""

    name: str = ""  # subclass overrides
    REQUEST_DELAY_SECONDS = 1.5

    def __init__(self, client: Optional[httpx.Client] = None):
        self._owns_client = client is None
        self._client = client or httpx.Client(
            http2=True,
            timeout=15.0,
            headers={"User-Agent": "coin-careerops/0.1"},
        )
        self._last_request_at = 0.0

    def __del__(self):
        if getattr(self, "_owns_client", False):
            try:
                self._client.close()
            except Exception:
                pass

    @abstractmethod
    def fetch_listings(self, slug: str, lane: str) -> list[dict]:
        """Return a list of role dicts (see _to_role_dict for shape)."""

    @abstractmethod
    def fetch_detail(self, url: str) -> dict | None:
        """Return enriched detail dict for one role URL, or None on failure."""

    def _get(self, url: str, params: dict | None = None) -> httpx.Response | None:
        """GET with rate limit. Returns None on 4xx, 5xx, or network error."""
        delta = time.monotonic() - self._last_request_at
        if delta < self.REQUEST_DELAY_SECONDS:
            time.sleep(self.REQUEST_DELAY_SECONDS - delta)
        try:
            resp = self._client.get(url, params=params)
        except (httpx.HTTPError, httpx.TransportError) as e:
            print(f"[{self.name}] GET {url} failed: {e}")
            self._last_request_at = time.monotonic()
            return None
        self._last_request_at = time.monotonic()
        if resp.status_code >= 400:
            return None
        return resp

    def _parse_comp(self, text: str | None) -> tuple[int | None, int | None]:
        return parse_comp_string(text)

    def _is_remote(self, location_text: str | None) -> bool:
        if not location_text:
            return False
        return bool(REMOTE_PATTERN.search(location_text))

    def _normalize_location(self, loc) -> str:
        if loc is None:
            return ""
        if isinstance(loc, str):
            return loc
        if isinstance(loc, dict):
            return loc.get("name") or loc.get("location") or ""
        if isinstance(loc, list) and loc:
            first = loc[0]
            return first if isinstance(first, str) else (first.get("name") or first.get("location") or "")
        return str(loc)

    def _to_role_dict(
        self,
        *,
        url: str,
        title: str,
        company: str,
        location: str,
        remote: bool,
        comp_min: int | None,
        comp_max: int | None,
        comp_source: str,
        comp_currency: str = "USD",
        posted_at: str | None,
        jd_raw: str | None,
    ) -> dict:
        return {
            "url": url,
            "title": title,
            "company": company,
            "location": location,
            "remote": int(bool(remote)),
            "comp_min": comp_min,
            "comp_max": comp_max,
            "comp_source": comp_source,
            "comp_currency": comp_currency,
            "source": self.name,
            "posted_at": posted_at,
            "jd_raw": jd_raw,
            "lane": None,  # set by orchestrator
        }
