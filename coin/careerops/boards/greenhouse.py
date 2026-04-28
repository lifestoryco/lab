"""Greenhouse public job-board scraper.

Pattern adapted from santifer/career-ops scan.mjs (MIT).

Endpoint: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
"""
from __future__ import annotations

import re

from careerops.boards.base import BoardScraper, _regex_parse_comp, _strip_html
from careerops.compensation import parse_comp_string

_PAY_NAME_PATTERN = re.compile(r"salary|comp|pay", re.I)


class GreenhouseBoard(BoardScraper):
    name = "greenhouse"

    BASE = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

    def fetch_listings(self, slug: str, lane: str) -> list[dict]:
        url = self.BASE.format(slug=slug)
        resp = self._get(url, params={"content": "true"})
        if resp is None:
            return []
        try:
            data = resp.json()
        except ValueError:
            return []
        jobs = data.get("jobs") or []
        out: list[dict] = []
        for j in jobs:
            out.append(self._parse_job(j))
        return out

    def fetch_detail(self, url: str) -> dict | None:
        # Listings already include full content with content=true. No-op.
        return None

    # ── internals ────────────────────────────────────────────────────────────

    def _parse_job(self, j: dict) -> dict:
        title = j.get("title") or ""
        url = j.get("absolute_url") or ""
        location_text = self._normalize_location(j.get("location"))
        posted_at = j.get("updated_at") or j.get("first_published")
        content_html = j.get("content") or ""

        comp_min, comp_max, comp_source = self._extract_comp(j, content_html)
        jd_raw = _strip_html(content_html).strip() if content_html else None

        return self._to_role_dict(
            url=url,
            title=title,
            company="",  # set by orchestrator from TARGET_COMPANIES
            location=location_text,
            remote=self._is_remote(location_text),
            comp_min=comp_min,
            comp_max=comp_max,
            comp_source=comp_source,
            posted_at=posted_at,
            jd_raw=jd_raw,
        )

    def _extract_comp(
        self, j: dict, content_html: str
    ) -> tuple[int | None, int | None, str]:
        # Priority 1 — structured metadata
        for m in j.get("metadata") or []:
            name = (m.get("name") or "").strip()
            if not _PAY_NAME_PATTERN.search(name):
                continue
            value = m.get("value")
            # Greenhouse currency_range shape:
            # {"unit": "USD", "min_value": "102000.0", "max_value": "130000.0"}
            if isinstance(value, dict):
                mn = value.get("min_value") or value.get("min")
                mx = value.get("max_value") or value.get("max")
                if mn is not None and mx is not None:
                    try:
                        return int(float(mn)), int(float(mx)), "explicit"
                    except (TypeError, ValueError):
                        pass
                # Fallback: parse as string within dict
                pretty = value.get("display_value") or ""
                if pretty:
                    pmin, pmax = parse_comp_string(pretty)
                    if pmin is not None:
                        return pmin, pmax, "explicit"
            elif isinstance(value, str):
                pmin, pmax = parse_comp_string(value)
                if pmin is not None:
                    return pmin, pmax, "explicit"

        # Priority 2 — regex against rendered prose
        pmin, pmax = _regex_parse_comp(_strip_html(content_html))
        if pmin is not None:
            return pmin, pmax, "parsed"

        # Priority 3 — neither
        return None, None, "parsed"
