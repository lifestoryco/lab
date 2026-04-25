"""LinkedIn people-search HTML parser + connection upsert.

Pure HTML-in / dict-out — no I/O for the parser. The companion
`upsert_scraped` writes parsed rows into the `connections` table via
`scripts/import_linkedin_connections.py::ensure_schema` semantics.

Designed to be the consumer half of `modes/network-scan.md` Step 3
(live-scrape fallback): the host Claude Code session uses the browser MCP
tool to navigate to `linkedin.com/search/results/people/?company=X` and
read the page HTML, then pipes that HTML into `parse_linkedin_people_search`
here. We never log into LinkedIn from Python — the browser session
belongs to Sean and we only consume the HTML he can see logged-in.

The parser is tolerant of LinkedIn's frequent class-name churn: it tries
multiple selector shapes and falls back to a structural walk of result
cards rather than relying on a single class hierarchy.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, Tag

# Selectors for the result card root. LinkedIn rotates these every few
# months (li.entity-result vs li.reusable-search__result-container vs
# li[class*="ember-view"]). Try in order; first hit wins.
_RESULT_CARD_SELECTORS = (
    "li.reusable-search__result-container",
    "li.entity-result",
    "div.entity-result",
    "li[class*='reusable-search']",
    "li[class*='entity-result']",
)

# Within a card, anchors to the profile have href starting with /in/ when
# inside the SPA but become absolute when SSR'd. Match either.
_PROFILE_HREF_RE = re.compile(r"^(?:https?://[^/]*linkedin\.com)?/in/([A-Za-z0-9_\-%]+)")

# Title/subtitle classes also rotate; pull them by data-test-id when
# possible, fall back to class-name partial match.
_TITLE_PARTIAL_CLASSES = (
    "entity-result__title-text",
    "entity-result__title-line",
    "search-result__title",
)
_PRIMARY_SUBTITLE_PARTIAL = (
    "entity-result__primary-subtitle",
    "search-result__subtitle",
)
_SECONDARY_SUBTITLE_PARTIAL = (
    "entity-result__secondary-subtitle",
)


def _has_partial_class(node: Tag, fragments: tuple[str, ...]) -> bool:
    classes = node.get("class") or []
    if isinstance(classes, str):
        classes = classes.split()
    blob = " ".join(classes)
    return any(frag in blob for frag in fragments)


def _find_result_cards(soup: BeautifulSoup) -> list[Tag]:
    for sel in _RESULT_CARD_SELECTORS:
        cards = soup.select(sel)
        if cards:
            return cards
    return []


def _extract_profile_url_and_name(card: Tag) -> tuple[str | None, str | None]:
    for a in card.find_all("a", href=True):
        href = a["href"].split("?")[0]  # strip tracking params
        m = _PROFILE_HREF_RE.match(href)
        if not m:
            continue
        slug = m.group(1)
        url = f"https://www.linkedin.com/in/{slug}"
        # The visible text on the title anchor is the name. Sometimes the
        # name is wrapped in a span with aria-hidden="true" plus a
        # screen-reader-only span; prefer the aria-hidden span if present.
        name = None
        aria = a.find(attrs={"aria-hidden": "true"})
        if aria and aria.get_text(strip=True):
            name = aria.get_text(strip=True)
        else:
            txt = a.get_text(" ", strip=True)
            if txt:
                # LinkedIn appends a connection degree like "• 2nd" — strip it.
                name = re.sub(r"\s*•\s*(?:1st|2nd|3rd|3rd\+)\s*$", "", txt).strip()
        return url, name
    return None, None


def _extract_subtitle(card: Tag, fragments: tuple[str, ...]) -> str | None:
    for node in card.find_all(True):
        if _has_partial_class(node, fragments):
            txt = node.get_text(" ", strip=True)
            if txt:
                return txt
    return None


def parse_linkedin_people_search(html: str, target_company: str | None = None) -> list[dict]:
    """Extract result cards from a LinkedIn /search/results/people/ HTML page.

    Returns a list of dicts with keys ready for upsert into `connections`:
      { full_name, first_name, last_name, linkedin_url, position,
        company, company_normalized }

    `target_company`: if provided, used to populate `company` for every row
    (the people-search page filters by company so the result set IS the
    company's employees, but the per-card HTML does NOT consistently include
    the company string). Pass the same string Sean passed to /coin network-scan.

    Skips cards we can't parse cleanly (no profile URL or no name) — the
    parser is best-effort, never raises on malformed HTML.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    cards = _find_result_cards(soup)
    out: list[dict] = []

    # Lazy import to avoid hard dep cycle with import script
    from scripts.import_linkedin_connections import (
        classify_seniority,
        normalize_company,
    )

    seen_urls: set[str] = set()
    for card in cards:
        url, name = _extract_profile_url_and_name(card)
        if not url or not name:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        position = _extract_subtitle(card, _TITLE_PARTIAL_CLASSES + _PRIMARY_SUBTITLE_PARTIAL)
        # Title-text node typically contains the name; the position lives
        # under primary-subtitle. If we got the name back from the title
        # anchor, _extract_subtitle on title fragments would re-return the
        # name. Specifically prefer primary-subtitle for position.
        primary = _extract_subtitle(card, _PRIMARY_SUBTITLE_PARTIAL)
        if primary and primary != name:
            position = primary

        # First/last split — LinkedIn names are unicode; just split on space.
        parts = name.split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""

        company = target_company or ""
        out.append({
            "first_name": first,
            "last_name": last,
            "full_name": name,
            "linkedin_url": url,
            "email": None,
            "company": company,
            "company_normalized": normalize_company(company),
            "position": position or "",
            "connected_on": None,  # unknown from search page
            "seniority": classify_seniority(position),
        })
    return out


def upsert_scraped(rows: Iterable[dict], db_path: str | Path) -> dict:
    """Upsert scraped connection rows. Returns inserted/updated counts.

    Mirrors the parameterized UPSERT pattern from
    scripts/import_linkedin_connections.py to stay consistent with the
    existing import path. Uses pre-SELECT existence checks (not
    cur.rowcount, which is unreliable on UPSERT) for accurate counts.
    """
    rows = list(rows)
    inserted = 0
    updated = 0
    if not rows:
        return {"rows_inserted": 0, "rows_updated": 0, "rows_processed": 0}

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        # Defensive: ensure the connections table exists. If it doesn't,
        # apply m003 inline so the scraper never fails on a fresh DB.
        existing = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='connections'"
        ).fetchone()
        if not existing:
            from scripts.migrations import m003_connections_outreach as m003
            conn.close()
            m003.apply(db_path)
            conn = sqlite3.connect(str(db_path))

        for row in rows:
            url = row["linkedin_url"]
            existed = conn.execute(
                "SELECT 1 FROM connections WHERE linkedin_url = ?", (url,)
            ).fetchone()
            conn.execute(
                """
                INSERT INTO connections
                    (first_name, last_name, full_name, linkedin_url, email,
                     company, company_normalized, position, connected_on, seniority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(linkedin_url) DO UPDATE SET
                    first_name        = excluded.first_name,
                    last_name         = excluded.last_name,
                    full_name         = excluded.full_name,
                    email             = COALESCE(excluded.email, connections.email),
                    company           = COALESCE(NULLIF(excluded.company, ''), connections.company),
                    company_normalized = COALESCE(NULLIF(excluded.company_normalized, ''), connections.company_normalized),
                    position          = excluded.position,
                    seniority         = excluded.seniority
                """,
                (
                    row["first_name"], row["last_name"], row["full_name"],
                    url, row.get("email"),
                    row.get("company") or "", row.get("company_normalized") or "",
                    row.get("position") or "",
                    row.get("connected_on"),
                    row.get("seniority") or "peer",
                ),
            )
            if existed:
                updated += 1
            else:
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return {
        "rows_inserted": inserted,
        "rows_updated": updated,
        "rows_processed": len(rows),
        "scraped_on": date.today().isoformat(),
    }
