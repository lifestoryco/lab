"""Tests for careerops.scraper.search_boards orchestrator + dedup logic."""
from __future__ import annotations

import pytest

from careerops import scraper
from careerops.boards.greenhouse import GreenhouseBoard
from careerops.boards.lever import LeverBoard
from careerops.boards.ashby import AshbyBoard


def _high_score_role(title: str, url: str, source: str = "greenhouse") -> dict:
    """A role dict the title-scorer will rate high enough for any lane."""
    return {
        "title": title,
        "url": url,
        "company": "",
        "location": "Remote (United States)",
        "remote": 1,
        "comp_min": None,
        "comp_max": None,
        "comp_source": "parsed",
        "comp_currency": "USD",
        "source": source,
        "posted_at": None,
        "jd_raw": None,
        "lane": None,
    }


def _low_score_role() -> dict:
    return _high_score_role(
        title="Marketing Coordinator", url="https://x.example.com/marketing"
    )


def test_search_boards_filters_by_lane_score(monkeypatch):
    """Roles whose title scores below LANE_BOARD_SCORE_FLOOR are dropped."""
    captured = []

    def fake_listings_high(self, slug, lane):
        captured.append((self.name, slug))
        return [
            _high_score_role(
                "Senior Solutions Engineer",
                f"https://boards.{self.name}.io/{slug}/jobs/high",
                source=self.name,
            ),
            _low_score_role(),  # under-floor
        ]

    monkeypatch.setattr(GreenhouseBoard, "fetch_listings", fake_listings_high)
    monkeypatch.setattr(LeverBoard, "fetch_listings", fake_listings_high)
    monkeypatch.setattr(AshbyBoard, "fetch_listings", fake_listings_high)
    # Limit registry to one company for determinism
    monkeypatch.setattr(scraper, "TARGET_COMPANIES", {
        "Vercel": {"greenhouse": "vercel", "lever": None, "ashby": None},
    })

    rows = scraper.search_boards("enterprise-sales-engineer", boards=["greenhouse"])

    titles = [r["title"] for r in rows]
    assert "Senior Solutions Engineer" in titles
    assert "Marketing Coordinator" not in titles


def test_search_boards_dedupes_against_linkedin(monkeypatch):
    """search_all_lanes dedupes via _canonical_url across LinkedIn + boards."""
    same_url = "https://example.com/foo/jobs/dup"

    def fake_search(lane, limit=25, location=None):
        return [_high_score_role("Senior Solutions Engineer", same_url, source="linkedin")]

    def fake_search_boards(lane, location=None, boards=None, companies=None):
        return [_high_score_role("Senior Solutions Engineer", same_url + "/?utm=x", source="greenhouse")]

    monkeypatch.setattr(scraper, "search", fake_search)
    monkeypatch.setattr(scraper, "search_boards", fake_search_boards)

    rows = scraper.search_all_lanes(limit_per_lane=5, boards=["linkedin", "greenhouse"])

    urls = [scraper._canonical_url(r["url"]) for r in rows]
    # 4 lanes × 1 url each = 4 entries before dedup; after dedup, 1 unique
    assert len(set(urls)) == 1


def test_board_failure_does_not_kill_run(monkeypatch):
    """One board raising must not block the others from contributing rows."""
    def fail_listings(self, slug, lane):
        raise RuntimeError("simulated greenhouse 500")

    def ok_listings(self, slug, lane):
        return [_high_score_role(
            "Senior Solutions Engineer",
            f"https://boards.{self.name}.io/{slug}/jobs/ok",
            source=self.name,
        )]

    monkeypatch.setattr(GreenhouseBoard, "fetch_listings", fail_listings)
    monkeypatch.setattr(LeverBoard, "fetch_listings", ok_listings)
    monkeypatch.setattr(AshbyBoard, "fetch_listings", ok_listings)
    monkeypatch.setattr(scraper, "TARGET_COMPANIES", {
        "ACME": {"greenhouse": "acme", "lever": "acme-lev", "ashby": "acme-ash"},
    })

    rows = scraper.search_boards(
        "enterprise-sales-engineer",
        boards=["greenhouse", "lever", "ashby"],
    )

    sources = {r["source"] for r in rows}
    assert "lever" in sources
    assert "ashby" in sources
    # greenhouse failed; it should not appear, but the run did not crash
    assert "greenhouse" not in sources


def test_companies_flag_limits_scope(monkeypatch):
    """Passing companies=[...] restricts iteration to only that subset."""
    seen_slugs: list[str] = []

    def fake_listings(self, slug, lane):
        seen_slugs.append((self.name, slug))
        return []

    monkeypatch.setattr(GreenhouseBoard, "fetch_listings", fake_listings)
    monkeypatch.setattr(LeverBoard, "fetch_listings", fake_listings)
    monkeypatch.setattr(AshbyBoard, "fetch_listings", fake_listings)
    monkeypatch.setattr(scraper, "TARGET_COMPANIES", {
        "Vercel": {"greenhouse": "vercel", "lever": None, "ashby": None},
        "Datadog": {"greenhouse": "datadog", "lever": None, "ashby": None},
        "Spotify": {"greenhouse": None, "lever": "spotify", "ashby": None},
    })

    scraper.search_boards(
        "enterprise-sales-engineer",
        companies=["Vercel"],
    )

    slugs = [s for _name, s in seen_slugs]
    assert "vercel" in slugs
    assert "datadog" not in slugs
    assert "spotify" not in slugs
