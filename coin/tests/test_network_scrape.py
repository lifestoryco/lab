"""Tests for careerops.network_scrape — LinkedIn people-search HTML parser
+ upsert_scraped path."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops.network_scrape import (
    parse_linkedin_people_search,
    upsert_scraped,
)
from scripts.migrations import m003_connections_outreach as m003

FIXTURE = ROOT / "tests" / "fixtures" / "network" / "sample_search_page.html"


@pytest.fixture(scope="module")
def html() -> str:
    return FIXTURE.read_text()


def test_parser_extracts_three_unique_cards(html):
    """Fixture has 5 cards: 3 valid, 1 malformed (no URL), 1 duplicate URL."""
    rows = parse_linkedin_people_search(html, target_company="Cox Communications")
    assert len(rows) == 3
    urls = {r["linkedin_url"] for r in rows}
    assert urls == {
        "https://www.linkedin.com/in/jane-doe-cox",
        "https://www.linkedin.com/in/john-smith-cox",
        "https://www.linkedin.com/in/alice-recruiter",
    }


def test_parser_strips_connection_degree_from_name(html):
    rows = parse_linkedin_people_search(html, target_company="Cox")
    jane = next(r for r in rows if "jane-doe" in r["linkedin_url"])
    assert jane["full_name"] == "Jane Doe"
    assert "•" not in jane["full_name"]
    assert "2nd" not in jane["full_name"]


def test_parser_strips_url_tracking_params(html):
    rows = parse_linkedin_people_search(html, target_company="Cox")
    jane = next(r for r in rows if "jane-doe" in r["linkedin_url"])
    # Query string ?refUrl=foo must be gone
    assert "?" not in jane["linkedin_url"]
    assert jane["linkedin_url"] == "https://www.linkedin.com/in/jane-doe-cox"


def test_parser_normalizes_relative_profile_urls(html):
    """LinkedIn SSR uses /in/<slug>; SPA uses absolute. Both must produce
    the same normalized https URL."""
    rows = parse_linkedin_people_search(html, target_company="Cox")
    john = next(r for r in rows if "john-smith" in r["linkedin_url"])
    assert john["linkedin_url"].startswith("https://www.linkedin.com/in/")


def test_parser_classifies_seniority(html):
    rows = parse_linkedin_people_search(html, target_company="Cox")
    by_url = {r["linkedin_url"]: r for r in rows}
    assert by_url["https://www.linkedin.com/in/jane-doe-cox"]["seniority"] == "leadership"
    assert by_url["https://www.linkedin.com/in/john-smith-cox"]["seniority"] == "senior_ic"
    # "Talent Acquisition Lead" — has 'lead' so senior_ic at import time
    assert by_url["https://www.linkedin.com/in/alice-recruiter"]["seniority"] == "senior_ic"


def test_parser_propagates_target_company(html):
    rows = parse_linkedin_people_search(html, target_company="Cox Communications, Inc.")
    for r in rows:
        assert r["company"] == "Cox Communications, Inc."
        assert r["company_normalized"] == "cox communications"


def test_parser_handles_empty_html():
    assert parse_linkedin_people_search("") == []
    assert parse_linkedin_people_search("<html><body>nothing here</body></html>") == []


def test_upsert_scraped_creates_schema_if_missing(tmp_path, html):
    """Fresh DB with no migrations applied — upsert must run m003 inline."""
    db = tmp_path / "fresh.db"
    rows = parse_linkedin_people_search(html, target_company="Cox")
    result = upsert_scraped(rows, db)
    assert result["rows_processed"] == 3
    assert result["rows_inserted"] == 3
    assert result["rows_updated"] == 0
    # Schema was created on the fly
    conn = sqlite3.connect(str(db))
    n = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
    conn.close()
    assert n == 3


def test_upsert_scraped_idempotent(tmp_path, html):
    db = tmp_path / "test.db"
    m003.apply(db)
    rows = parse_linkedin_people_search(html, target_company="Cox")
    upsert_scraped(rows, db)
    second = upsert_scraped(rows, db)
    # Second run: 0 inserted, 3 updated (no duplicates)
    assert second["rows_inserted"] == 0
    assert second["rows_updated"] == 3
    conn = sqlite3.connect(str(db))
    n = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
    conn.close()
    assert n == 3


def test_upsert_scraped_preserves_company_when_export_first(tmp_path):
    """If a row was first imported from the CSV (real company string) and
    then re-seen by the scraper (which only knows the search-target company),
    the COALESCE in the upsert must NOT clobber the more-specific export
    string with the scraper's generic target."""
    db = tmp_path / "test.db"
    m003.apply(db)
    # Seed via CSV-like insert with a specific company
    conn = sqlite3.connect(str(db))
    conn.execute(
        "INSERT INTO connections (linkedin_url, full_name, company, company_normalized, position, seniority) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("https://www.linkedin.com/in/jane-doe-cox", "Jane Doe",
         "Cox Communications, Inc.", "cox communications",
         "VP Eng", "leadership"),
    )
    conn.commit()
    conn.close()
    # Now scrape with empty target_company
    upsert_scraped(
        [{
            "first_name": "Jane", "last_name": "Doe", "full_name": "Jane Doe",
            "linkedin_url": "https://www.linkedin.com/in/jane-doe-cox",
            "email": None, "company": "", "company_normalized": "",
            "position": "VP Engineering", "connected_on": None,
            "seniority": "leadership",
        }],
        db,
    )
    conn = sqlite3.connect(str(db))
    row = conn.execute(
        "SELECT company, company_normalized, position FROM connections "
        "WHERE linkedin_url = ?",
        ("https://www.linkedin.com/in/jane-doe-cox",),
    ).fetchone()
    conn.close()
    assert row[0] == "Cox Communications, Inc."  # original preserved
    assert row[1] == "cox communications"
    assert row[2] == "VP Engineering"  # position updated
