"""Ashby public job-board scraper.

Pattern adapted from santifer/career-ops scan.mjs (MIT).

Endpoint: https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true
"""
from __future__ import annotations

from careerops.boards.base import BoardScraper, _regex_parse_comp
from careerops.compensation import parse_comp_string


class AshbyBoard(BoardScraper):
    name = "ashby"

    BASE = "https://api.ashbyhq.com/posting-api/job-board/{slug}"

    def fetch_listings(self, slug: str, lane: str) -> list[dict]:
        url = self.BASE.format(slug=slug)
        resp = self._get(url, params={"includeCompensation": "true"})
        if resp is None:
            return []
        try:
            data = resp.json()
        except ValueError:
            return []
        jobs = data.get("jobs") or []
        return [self._parse_job(j) for j in jobs]

    def fetch_detail(self, url: str) -> dict | None:
        return None

    # ── internals ────────────────────────────────────────────────────────────

    def _parse_job(self, j: dict) -> dict:
        title = j.get("title") or ""
        url = j.get("jobUrl") or j.get("applyUrl") or ""
        location_text = self._normalize_location(j.get("location"))
        posted_at = j.get("publishedAt")
        desc_plain = j.get("descriptionPlain") or ""

        comp_min, comp_max, comp_source = self._extract_comp(j, desc_plain)

        is_remote = bool(j.get("isRemote"))
        if not is_remote:
            wpt = (j.get("workplaceType") or "").lower()
            is_remote = self._is_remote(location_text) or wpt == "remote"

        return self._to_role_dict(
            url=url,
            title=title,
            company="",
            location=location_text,
            remote=is_remote,
            comp_min=comp_min,
            comp_max=comp_max,
            comp_source=comp_source,
            posted_at=posted_at,
            jd_raw=desc_plain.strip() or None,
        )

    def _extract_comp(
        self, j: dict, desc_plain: str
    ) -> tuple[int | None, int | None, str]:
        comp = j.get("compensation") or {}

        # Priority 1 — compensationTier with min/max numeric
        tier = comp.get("compensationTier") or {}
        if isinstance(tier, dict):
            mn = tier.get("minValue")
            mx = tier.get("maxValue")
            if mn is not None and mx is not None:
                try:
                    return int(mn), int(mx), "explicit"
                except (TypeError, ValueError):
                    pass

        # Priority 1b — newer shape: list of compensationTiers, each with components
        tiers = comp.get("compensationTiers") or []
        if isinstance(tiers, list):
            for t in tiers:
                comps = t.get("components") or []
                for c in comps:
                    mn = c.get("minValue")
                    mx = c.get("maxValue")
                    if mn is not None and mx is not None:
                        try:
                            return int(mn), int(mx), "explicit"
                        except (TypeError, ValueError):
                            pass

        # Priority 2 — compensationTierSummary (string like "$170K - $220K")
        summary = comp.get("compensationTierSummary") or comp.get(
            "scrapeableCompensationSalarySummary"
        )
        if summary:
            pmin, pmax = parse_comp_string(summary)
            if pmin is not None:
                return pmin, pmax, "explicit"

        # Priority 3 — regex on descriptionPlain
        pmin, pmax = _regex_parse_comp(desc_plain)
        if pmin is not None:
            return pmin, pmax, "parsed"

        return None, None, "parsed"
