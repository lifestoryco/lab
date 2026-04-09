"""
pokequant/scraper.py
---------------------
Live Data Scraper — PriceCharting.com + pokemontcg.io

Fetches real sold-listing data for raw (ungraded) Pokémon cards.
All results are cached in a local SQLite database for 24 hours so
repeated calls are instant and don't hammer the source sites.

Usage:
  python pokequant/scraper.py --card "Charizard V" --days 30
  python pokequant/scraper.py --card "Umbreon VMAX" --days 14 --no-cache
  python pokequant/scraper.py --card "Pikachu" --source tcgapi

Output (stdout):
  JSON array of sale records, OR a single error object:
    [{"sale_id": "pc_001", "price": 36.50, "date": "2024-02-18",
      "condition": "NM", "source": "pricecharting", "quantity": 1}, ...]
    {"error": "No listings found for 'X'", "card": "X", "count": 0}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import random
import re
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Generator

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).parents[1]
_CACHE_DB = _BASE_DIR / "data" / "db" / "history.db"

# ---------------------------------------------------------------------------
# User-Agent rotation pool — 6 real browser fingerprints.
# Rotated randomly on every HTTP request to reduce detection risk.
# ---------------------------------------------------------------------------
_USER_AGENTS: list[str] = [
    # Chrome 121 / Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Chrome 121 / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Firefox 122 / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) "
    "Gecko/20100101 Firefox/122.0",
    # Firefox 122 / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:122.0) "
    "Gecko/20100101 Firefox/122.0",
    # Safari 17 / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Edge 121 / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]

# ---------------------------------------------------------------------------
# Graded card filter — drop any listing whose title/description contains
# these strings (case-insensitive). We want raw card prices only.
# ---------------------------------------------------------------------------
_GRADED_KEYWORDS: frozenset[str] = frozenset(
    {"PSA", "CGC", "BGS", "SGC", "HGA", "Graded", "graded"}
)

# ---------------------------------------------------------------------------
# PriceCharting URL helpers
# ---------------------------------------------------------------------------
_PC_BASE = "https://www.pricecharting.com"

# Known set-name → URL slug mappings.  Add entries as needed.
_SET_SLUGS: dict[str, str] = {
    "sword & shield base": "sword-shield",
    "sword and shield base": "sword-shield",
    "evolving skies": "evolving-skies",
    "brilliant stars": "brilliant-stars",
    "lost origin": "lost-origin",
    "silver tempest": "silver-tempest",
    "crown zenith": "crown-zenith",
    "paldea evolved": "paldea-evolved",
    "obsidian flames": "obsidian-flames",
    "paradox rift": "paradox-rift",
    "temporal forces": "temporal-forces",
    "twilight masquerade": "twilight-masquerade",
    "stellar crown": "stellar-crown",
    "surging sparks": "surging-sparks",
    "prismatic evolutions": "prismatic-evolutions",
    "151": "scarlet-violet-151",
    "scarlet & violet base": "scarlet-violet",
}

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cache layer
# ---------------------------------------------------------------------------


def _init_cache_db() -> None:
    """Create the history.db cache table if it doesn't exist."""
    _CACHE_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(_CACHE_DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scrape_cache (
                card_slug   TEXT NOT NULL,
                source      TEXT NOT NULL,
                fetched_at  TEXT NOT NULL,
                payload     TEXT NOT NULL,
                PRIMARY KEY (card_slug, source)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_slug_source "
            "ON scrape_cache(card_slug, source)"
        )
        conn.commit()


def _cache_get(card_slug: str, source: str) -> list[dict] | None:
    """Return cached payload if it is < 24 hours old, else None."""
    _init_cache_db()
    with sqlite3.connect(_CACHE_DB) as conn:
        row = conn.execute(
            """
            SELECT payload FROM scrape_cache
            WHERE card_slug = ? AND source = ?
              AND fetched_at > datetime('now', '-24 hours')
            """,
            (card_slug, source),
        ).fetchone()
    if row:
        logger.info("Cache HIT for '%s' (%s).", card_slug, source)
        return json.loads(row[0])
    logger.info("Cache MISS for '%s' (%s) — will fetch live.", card_slug, source)
    return None


def _cache_put(card_slug: str, source: str, payload: list[dict]) -> None:
    """Write or replace a cache entry."""
    _init_cache_db()
    with sqlite3.connect(_CACHE_DB) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO scrape_cache
                (card_slug, source, fetched_at, payload)
            VALUES (?, ?, datetime('now'), ?)
            """,
            (card_slug, source, json.dumps(payload)),
        )
        conn.commit()
    logger.debug("Cached %d records for '%s' (%s).", len(payload), card_slug, source)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get(url: str, timeout: int = 10) -> requests.Response:
    """HTTP GET with random User-Agent and polite retry (1 retry on 429)."""
    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "DNT": "1",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code == 429:
        # Back off once on rate-limit.
        logger.warning("Rate limited by %s — backing off 5s.", url)
        time.sleep(5)
        headers["User-Agent"] = random.choice(_USER_AGENTS)  # Rotate UA on retry.
        resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp


# ---------------------------------------------------------------------------
# Name → slug conversion
# ---------------------------------------------------------------------------


def _card_name_to_slug(name: str) -> str:
    """Convert a card name to a PriceCharting URL slug.

    Examples:
      "Charizard V"              → "charizard-v"
      "Umbreon VMAX (Alt Art)"   → "umbreon-vmax-alt-art"
      "Pikachu ex"               → "pikachu-ex"
    """
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", " ", slug)  # Remove special chars (except hyphens)
    slug = re.sub(r"\s+", "-", slug.strip())    # Spaces → hyphens
    slug = re.sub(r"-+", "-", slug)             # Collapse multiple hyphens
    return slug


# ---------------------------------------------------------------------------
# Graded listing filter
# ---------------------------------------------------------------------------


def _is_graded(title: str) -> bool:
    """Return True if a listing title indicates a professionally graded card."""
    title_upper = title.upper()
    return any(kw.upper() in title_upper for kw in _GRADED_KEYWORDS)


def _parse_condition(title: str) -> str:
    """Extract condition from a listing title string.

    PriceCharting listing titles often include condition in the item name.
    We do a best-effort parse — unknown defaults to "NM".
    """
    t = title.upper()
    if "MINT" in t or "NM" in t or "NEAR MINT" in t:
        return "NM"
    if "LIGHTLY PLAYED" in t or "LP" in t:
        return "LP"
    if "MODERATELY PLAYED" in t or "MP" in t:
        return "MP"
    if "HEAVILY PLAYED" in t or "HP" in t:
        return "HP"
    if "DAMAGED" in t or "DMG" in t:
        return "DM"
    return "NM"  # Default assumption for raw listings without explicit condition.


# ---------------------------------------------------------------------------
# PriceCharting scraper
# ---------------------------------------------------------------------------


def _build_pricecharting_url(card_name: str, set_name: str | None = None) -> str:
    """Construct a PriceCharting completed-auction URL for a card.

    Tries set-specific URL first; falls back to generic search URL.
    """
    card_slug = _card_name_to_slug(card_name)

    if set_name:
        set_key = set_name.lower().strip()
        set_slug = _SET_SLUGS.get(set_key)
        if set_slug:
            # e.g. /game/pokemon-evolving-skies/umbreon-vmax-alt-art#completed-auctions
            return f"{_PC_BASE}/game/pokemon-{set_slug}/{card_slug}#completed-auctions"

    # Generic fallback — PriceCharting search page.
    return f"{_PC_BASE}/search-products?q={card_slug.replace('-', '+')}&type=prices"


def _scrape_pricecharting(
    card_name: str,
    set_name: str | None = None,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Scrape completed sales from PriceCharting.com.

    Targets the `#completed_auctions` table. Filters out graded listings.
    Returns up to `days` worth of sales as a list of sale dicts.

    Parameters
    ----------
    card_name : str
        Human-readable card name (e.g. "Charizard V").
    set_name : str or None
        Optional set to narrow the URL.
    days : int
        How many calendar days of history to collect.

    Returns
    -------
    list[dict]
        Sale records, or empty list on scrape failure.
    """
    url = _build_pricecharting_url(card_name, set_name)
    logger.info("Scraping PriceCharting: %s", url)

    try:
        resp = _get(url)
    except requests.RequestException as exc:
        logger.error("PriceCharting request failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # PriceCharting renders completed sales in a table with id="completed_auctions"
    table = soup.find("table", {"id": "completed_auctions"})
    if not table:
        logger.warning("No completed_auctions table found at %s", url)
        return []

    cutoff_date = datetime.utcnow().date() - timedelta(days=days)
    sales: list[dict[str, Any]] = []
    counter = 0

    for row in table.find_all("tr")[1:]:  # Skip header row.
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # --- Extract listing title (column varies by page layout) ---
        title_tag = row.find("a") or row.find("td", class_="title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Drop graded cards immediately.
        if _is_graded(title):
            logger.debug("Dropping graded listing: %s", title[:60])
            continue

        # --- Extract price ---
        price_text = ""
        for col in cols:
            text = col.get_text(strip=True)
            # PriceCharting prices look like "$36.50" or "36.50"
            if re.match(r"^\$?[\d,]+\.\d{2}$", text.replace(",", "")):
                price_text = text
                break

        if not price_text:
            continue

        try:
            price = float(price_text.replace("$", "").replace(",", ""))
        except ValueError:
            continue

        # Skip physically impossible prices.
        if price < 0.10 or price > 50_000:
            continue

        # --- Extract sale date ---
        date_text = ""
        for col in cols:
            text = col.get_text(strip=True)
            # PriceCharting dates look like "Feb 18, 2024" or "2024-02-18"
            if re.search(r"\d{4}", text) and len(text) < 20:
                date_text = text
                break

        try:
            if re.match(r"\d{4}-\d{2}-\d{2}", date_text):
                sale_date = datetime.strptime(date_text[:10], "%Y-%m-%d").date()
            else:
                # Try "Mon DD, YYYY" format.
                sale_date = datetime.strptime(date_text, "%b %d, %Y").date()
        except (ValueError, TypeError):
            sale_date = datetime.utcnow().date()

        # Filter by date window.
        if sale_date < cutoff_date:
            continue

        counter += 1
        condition = _parse_condition(title)

        # Deterministic sale_id based on price + date + counter.
        sale_id_src = f"pc_{card_name}_{sale_date}_{price}_{counter}"
        sale_id = "pc_" + hashlib.md5(sale_id_src.encode()).hexdigest()[:8]

        sales.append(
            {
                "sale_id": sale_id,
                "price": round(price, 2),
                "date": sale_date.isoformat(),
                "condition": condition,
                "source": "pricecharting",
                "quantity": 1,
            }
        )

    logger.info(
        "PriceCharting: found %d raw sales → %d after graded filter.",
        counter + sum(1 for _ in table.find_all("tr")[1:]) - counter,
        len(sales),
    )
    return sales


# ---------------------------------------------------------------------------
# pokemontcg.io fallback (free, no API key required for card lookup)
# ---------------------------------------------------------------------------


def _fetch_tcgapi(card_name: str, days: int = 30) -> list[dict[str, Any]]:
    """Fetch market price data from the Pokémon TCG API (pokemontcg.io).

    This is a fallback / supplement — the API returns current TCGPlayer
    market prices, not individual sale records. We synthesize a small
    set of pseudo-sale-records from the price bands (low / mid / market)
    to give the analysis modules something to work with.

    Parameters
    ----------
    card_name : str
        Card name to search.
    days : int
        Number of synthetic "days" to spread the price points across
        (used for date assignment only — the prices are real).

    Returns
    -------
    list[dict]
        Up to 3 synthetic sale records, or empty list on failure.
    """
    url = "https://api.pokemontcg.io/v2/cards"
    params = {"q": f'name:"{card_name}"', "select": "id,name,tcgplayer,cardmarket"}

    logger.info("Falling back to pokemontcg.io for '%s'.", card_name)

    try:
        resp = _get(url)
        data = resp.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("pokemontcg.io request failed: %s", exc)
        return []

    cards = data.get("data", [])
    if not cards:
        return []

    # Use the first matching card.
    card = cards[0]
    sales: list[dict[str, Any]] = []

    today = datetime.utcnow().date()

    # Extract price points from TCGPlayer prices.
    tcg = card.get("tcgplayer", {}).get("prices", {})
    for variant_name, prices in tcg.items():
        if not isinstance(prices, dict):
            continue
        for price_key, label in [
            ("market", "NM"),
            ("mid", "LP"),
            ("low", "HP"),
        ]:
            val = prices.get(price_key)
            if val and isinstance(val, (int, float)) and val > 0:
                offset = {"market": 0, "mid": 3, "low": 7}.get(price_key, 0)
                sale_date = today - timedelta(days=offset)
                sale_id = f"tcg_{card['id']}_{price_key}"
                sales.append(
                    {
                        "sale_id": sale_id,
                        "price": round(float(val), 2),
                        "date": sale_date.isoformat(),
                        "condition": label,
                        "source": "pokemontcg.io",
                        "quantity": 1,
                    }
                )

    logger.info("pokemontcg.io: synthesized %d price point(s) for '%s'.", len(sales), card_name)
    return sales


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_sales(
    card_name: str,
    set_name: str | None = None,
    days: int = 30,
    source: str = "pricecharting",
    use_cache: bool = True,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Fetch sold listings for a card, with SQLite caching.

    Parameters
    ----------
    card_name : str
        Card name as it appears on PriceCharting (e.g. "Charizard V").
    set_name : str or None
        Optional set name to narrow the PriceCharting URL.
    days : int
        How many days of sales history to retrieve.
    source : str
        "pricecharting" (default) or "tcgapi".
    use_cache : bool
        Set False to force a live fetch and overwrite the cache.

    Returns
    -------
    list[dict]
        Sale records on success.
    dict
        Error object: {"error": "...", "card": "...", "count": 0}
    """
    card_slug = _card_name_to_slug(card_name)

    # --- Cache check ---
    if use_cache:
        cached = _cache_get(card_slug, source)
        if cached is not None:
            return cached

    # --- Live fetch ---
    if source == "tcgapi":
        sales = _fetch_tcgapi(card_name, days=days)
    else:
        sales = _scrape_pricecharting(card_name, set_name=set_name, days=days)
        # If PriceCharting returned nothing, try the API fallback.
        if not sales:
            logger.info("PriceCharting returned 0 results — trying pokemontcg.io fallback.")
            sales = _fetch_tcgapi(card_name, days=days)

    # --- Handle empty result ---
    if not sales:
        return {
            "error": f"No listings found for '{card_name}'",
            "card": card_name,
            "count": 0,
        }

    # --- Save to cache ---
    _cache_put(card_slug, source, sales)

    return sales


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,  # Quiet by default; -v enables DEBUG
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    parser = argparse.ArgumentParser(
        description="Fetch Pokémon card sold listings → compact JSON stdout"
    )
    parser.add_argument("--card", required=True, help='Card name, e.g. "Charizard V"')
    parser.add_argument("--set", dest="set_name", default=None,
                        help='Optional set name, e.g. "Sword & Shield Base"')
    parser.add_argument("--days", type=int, default=30,
                        help="Days of sales history (default: 30)")
    parser.add_argument("--source", choices=["pricecharting", "tcgapi"],
                        default="pricecharting",
                        help="Data source (default: pricecharting)")
    parser.add_argument("--no-cache", dest="no_cache", action="store_true",
                        help="Bypass cache and force a live fetch")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging to stderr")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    result = fetch_sales(
        card_name=args.card,
        set_name=args.set_name,
        days=args.days,
        source=args.source,
        use_cache=not args.no_cache,
    )

    # Always output to stdout — Claude reads this.
    print(json.dumps(result, separators=(",", ":")))
