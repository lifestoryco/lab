"""Lever public job-board scraper.

Pattern adapted from santifer/career-ops scan.mjs (MIT).

Endpoint: https://api.lever.co/v0/postings/{slug}?mode=json
"""
from __future__ import annotations

from careerops.boards.base import BoardScraper, _regex_parse_comp


class LeverBoard(BoardScraper):
    name = "lever"

    BASE = "https://api.lever.co/v0/postings/{slug}"

    def fetch_listings(self, slug: str, lane: str) -> list[dict]:
        url = self.BASE.format(slug=slug)
        resp = self._get(url, params={"mode": "json"})
        if resp is None:
            return []
        try:
            data = resp.json()
        except ValueError:
            return []
        if not isinstance(data, list):
            return []
        return [self._parse_posting(p) for p in data]

    def fetch_detail(self, url: str) -> dict | None:
        return None

    # ── internals ────────────────────────────────────────────────────────────

    def _parse_posting(self, p: dict) -> dict:
        title = p.get("text") or ""
        url = p.get("hostedUrl") or p.get("applyUrl") or ""
        cats = p.get("categories") or {}
        location_text = (
            cats.get("location")
            or cats.get("allLocations", [None])[0]
            if cats
            else ""
        ) or ""
        posted_at_ms = p.get("createdAt")
        posted_at = self._ms_to_iso(posted_at_ms) if posted_at_ms else None

        desc = (p.get("descriptionPlain") or "") + "\n" + (p.get("additionalPlain") or "")
        comp_min, comp_max, comp_source = self._extract_comp(p, desc)

        # workplaceType also signals remote in newer Lever postings
        wpt = (cats.get("workplaceType") or "").lower() if cats else ""
        remote = self._is_remote(location_text) or wpt == "remote"

        return self._to_role_dict(
            url=url,
            title=title,
            company="",  # orchestrator overwrites
            location=location_text,
            remote=remote,
            comp_min=comp_min,
            comp_max=comp_max,
            comp_source=comp_source,
            posted_at=posted_at,
            jd_raw=desc.strip() or None,
        )

    def _extract_comp(self, p: dict, desc: str) -> tuple[int | None, int | None, str]:
        # Priority 1 — structured salaryRange
        sr = p.get("salaryRange")
        if isinstance(sr, dict):
            mn, mx = sr.get("min"), sr.get("max")
            if mn is not None and mx is not None:
                try:
                    return int(mn), int(mx), "explicit"
                except (TypeError, ValueError):
                    pass

        # Priority 2 — regex on description prose
        pmin, pmax = _regex_parse_comp(desc)
        if pmin is not None:
            return pmin, pmax, "parsed"

        return None, None, "parsed"

    @staticmethod
    def _ms_to_iso(ms: int) -> str | None:
        try:
            from datetime import datetime, timezone
            return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat()
        except (TypeError, ValueError, OSError):
            return None
