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
import os
import json
import logging
import random
import re
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Generator

import requests

from pokequant.http import session as _http_session
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_BASE_DIR = Path(__file__).parents[1]


def _resolve_cache_db() -> Path:
    """Pick the sqlite cache path, preferring /tmp on read-only serverless FS.

    Vercel's filesystem is read-only outside /tmp. If HOLO_CACHE_DB isn't set
    but we detect a Vercel environment, default to /tmp so import never
    explodes on cold-start.
    """
    env_path = os.environ.get("HOLO_CACHE_DB")
    if env_path:
        return Path(env_path)
    if os.environ.get("VERCEL"):
        return Path("/tmp/holo_cache.db")
    return _BASE_DIR / "data" / "db" / "history.db"


_CACHE_DB = _resolve_cache_db()

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

_CACHE_READY: bool = False


# ---------------------------------------------------------------------------
# Cache layer
# ---------------------------------------------------------------------------


def _init_cache_db() -> None:
    """Create the history.db cache tables if they don't exist. Called once at startup.

    NEVER prints to stdout and NEVER calls sys.exit — this runs inside the Vercel
    request handler and stdout must stay clean for the JSON protocol. On failure
    we silently fall back to /tmp/holo_cache.db once; if that also fails we log
    a stderr warning and let callers proceed (downstream code already treats
    cache misses gracefully).
    """
    global _CACHE_READY, _CACHE_DB
    if _CACHE_READY:
        return

    def _try_init(path: Path) -> bool:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS scrape_cache (
                        card_slug   TEXT NOT NULL,
                        source      TEXT NOT NULL,
                        fetched_at  TEXT NOT NULL,
                        payload     TEXT NOT NULL,
                        PRIMARY KEY (card_slug, source)
                    )
                """)
                # Permanent cache: pokemontcg card_id → TCGPlayer product_id.
                # No TTL — product IDs don't change.
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tcgplayer_product_ids (
                        pokemontcg_id   TEXT PRIMARY KEY,
                        product_id      INTEGER NOT NULL
                    )
                """)
                conn.commit()
            return True
        except Exception:
            return False

    if _try_init(_CACHE_DB):
        _CACHE_READY = True
        return

    fallback = Path("/tmp/holo_cache.db")
    if fallback != _CACHE_DB and _try_init(fallback):
        print(
            f"[scraper] cache init failed at {_CACHE_DB}, using fallback {fallback}",
            file=sys.stderr,
        )
        _CACHE_DB = fallback
        _CACHE_READY = True
        return

    print(
        f"[scraper] cache init failed at {_CACHE_DB} and fallback {fallback}; "
        f"continuing without cache",
        file=sys.stderr,
    )


def _product_id_cache_get(pokemontcg_id: str) -> int | None:
    """Return a cached TCGPlayer product ID, or None if not stored."""
    with sqlite3.connect(_CACHE_DB) as conn:
        row = conn.execute(
            "SELECT product_id FROM tcgplayer_product_ids WHERE pokemontcg_id = ?",
            (pokemontcg_id,),
        ).fetchone()
    return int(row[0]) if row else None


def _product_id_cache_put(pokemontcg_id: str, product_id: int) -> None:
    """Permanently store a pokemontcg card_id → TCGPlayer product_id mapping."""
    with sqlite3.connect(_CACHE_DB) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tcgplayer_product_ids (pokemontcg_id, product_id) VALUES (?, ?)",
            (pokemontcg_id, product_id),
        )
        conn.commit()
    logger.debug("Cached TCGPlayer product ID %d for '%s'.", product_id, pokemontcg_id)


def _cache_get(card_slug: str, source: str) -> list[dict] | None:
    """Return cached payload if it is < 24 hours old, else None."""
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


# Initialise the cache database once at import time.
_init_cache_db()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _get(url: str, timeout: int = 10, retries: int = 3) -> requests.Response:
    """HTTP GET with UA rotation, exponential backoff, and explicit error classification."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            headers = {
                "User-Agent": random.choice(_USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "DNT": "1",
            }
            resp = _http_session().get(url, headers=headers, timeout=timeout)

            if resp.status_code == 429:
                wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                logger.warning("Rate limited by %s — backing off %ds (attempt %d/%d).",
                               url, wait, attempt + 1, retries)
                time.sleep(wait)
                last_exc = None
                continue

            if resp.status_code == 403:
                raise ValueError(
                    f"Access denied by {url} (HTTP 403). "
                    "The site may be blocking automated requests. "
                    "Try again in a few minutes or check your User-Agent."
                )

            if resp.status_code >= 500:
                logger.warning("Server error %d from %s — retrying (attempt %d/%d).",
                               resp.status_code, url, attempt + 1, retries)
                time.sleep(3 * (attempt + 1))
                last_exc = ValueError(f"Server error {resp.status_code} from {url}")
                continue

            resp.raise_for_status()
            return resp

        except requests.exceptions.Timeout:
            logger.warning("Timeout after %ds fetching %s (attempt %d/%d).",
                           timeout, url, attempt + 1, retries)
            last_exc = ValueError(
                f"Request to {url} timed out after {timeout}s. "
                "The site may be slow. Try again shortly."
            )
            time.sleep(2 * (attempt + 1))

        except requests.exceptions.ConnectionError as exc:
            logger.warning("Connection error fetching %s: %s (attempt %d/%d).",
                           url, exc, attempt + 1, retries)
            last_exc = ValueError(
                f"Could not connect to {url}. Check your internet connection."
            )
            time.sleep(2 * (attempt + 1))

    raise last_exc or ValueError(f"Failed to fetch {url} after {retries} attempts.")


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


def _strip_card_number(name: str) -> str:
    """Remove trailing card number suffixes like '079/073' or '074/073'.

    Examples:
      "Charizard V 079/073" → "Charizard V"
      "Umbreon VMAX"        → "Umbreon VMAX"
    """
    return re.sub(r"\s+\d{3}/\d{3,4}$", "", name.strip())


def _best_card_match(cards: list[dict], card_name: str) -> dict | None:
    """Return the card from API results that best matches the human name.

    Prefers exact name match; falls back to highest word-overlap score.
    """
    if not cards:
        return None
    clean = _strip_card_number(card_name).lower()
    best: dict | None = None
    best_score = -1
    for card in cards:
        api_name = card.get("name", "").lower()
        if api_name == clean:
            return card  # Exact match — stop immediately.
        score = len(set(clean.split()) & set(api_name.split()))
        if score > best_score:
            best_score = score
            best = card
    return best


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


def _resolve_pricecharting_card_url(soup: BeautifulSoup, card_name: str) -> str | None:
    """From a PriceCharting search results page, find the best-matching card URL.

    PriceCharting search results use full absolute URLs in their product table.
    Scans anchor tags whose href contains /game/pokemon-, ranks by word overlap
    (and card number if present), and returns the best match or None.
    """
    clean = _strip_card_number(card_name).lower()
    name_words = set(clean.split())

    # Extract card number (e.g. "079" from "079/073") with leading zeros stripped.
    number_match = re.search(r"(\d{3})/\d{3}", card_name)
    card_number = str(int(number_match.group(1))) if number_match else None

    best_url: str | None = None
    best_score = -1

    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        # Accept both absolute and relative product URLs.
        if "/game/pokemon-" not in href:
            continue
        link_text = a.get_text(strip=True).lower()
        combined = f"{link_text} {href.lower()}"
        tokens = set(re.split(r"[\s/\-#%]+", combined))
        score = len(name_words & tokens)
        # Bonus point if the card number appears in the slug.
        if card_number and card_number in tokens:
            score += 2
        if score > best_score:
            best_score = score
            # Normalise to absolute URL.
            if href.startswith("http"):
                best_url = href
            else:
                best_url = f"{_PC_BASE}{href}"

    return best_url


# PriceCharting 2026 HTML structure: completed sales live in
# <div class="completed-auctions-{variant}"><table class="hoverable-rows sortable">
# where variant maps to grade tabs. We default to "used" (Ungraded / raw).
_PC_GRADE_CONTAINERS: dict[str, str] = {
    "raw":     "completed-auctions-used",       # Ungraded — what 90% of traders want
    "psa9":    "completed-auctions-graded",
    "psa10":   "completed-auctions-manual-only",
    "graded":  "completed-auctions-new",         # Grade 8 mixed-grade tab
}


def _scrape_pricecharting(
    card_name: str,
    set_name: str | None = None,
    days: int = 30,
    grade: str = "raw",
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
    except (requests.RequestException, ValueError) as exc:
        logger.error("PriceCharting request failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    def _find_sales_table(s: BeautifulSoup, grade: str):
        """Locate the completed-auctions table for a specific grade tab.

        PriceCharting 2026 card page has TWO divs with class="completed-auctions-used":
          1. The tab header button (class includes 'tab') — empty
          2. The data container (class is just 'completed-auctions-used') — has the table
        We must pick the one that actually contains a hoverable-rows table.

        Returns None for search-result pages (no matching container),
        so the caller can follow a product link instead of misparsing search rows.
        """
        container_class = _PC_GRADE_CONTAINERS.get(grade, _PC_GRADE_CONTAINERS["raw"])
        for container in s.find_all("div", class_=container_class):
            # Skip tab-header divs that don't actually hold sales data.
            if "tab" in (container.get("class") or []):
                continue
            t = container.find("table", class_="hoverable-rows")
            if t:
                return t
        # Legacy structure (pre-2026)
        return s.find("table", {"id": "completed_auctions"})

    table = _find_sales_table(soup, grade)
    resolved_url = url  # The URL that actually held the sales data (for source attribution).

    # If we landed on a search results page (no sales table), follow the best-matching product link.
    if not table:
        logger.info("No sales table at %s — scanning for product links.", url)
        card_url = _resolve_pricecharting_card_url(soup, card_name)
        if card_url:
            logger.info("Following product link: %s", card_url)
            try:
                resp = _get(card_url)
                soup = BeautifulSoup(resp.text, "html.parser")
                table = _find_sales_table(soup, grade)
                if table:
                    resolved_url = card_url  # Point source attribution to the real card page.
            except (requests.RequestException, ValueError) as exc:
                logger.error("Failed to follow product link %s: %s", card_url, exc)

    if not table:
        logger.warning("No sales table found for '%s' (grade=%s).", card_name, grade)
        return []

    cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=days)
    sales: list[dict[str, Any]] = []
    counter = 0
    graded_dropped: int = 0

    for row in table.find_all("tr")[1:]:  # Skip header row.
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # --- Extract listing title (column varies by page layout) ---
        title_tag = row.find("a") or row.find("td", class_="title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # For raw/ungraded tab, drop any graded listings that slipped through
        # (PriceCharting's tabs are authoritative but titles can still mention PSA etc.)
        if grade == "raw" and _is_graded(title):
            logger.debug("Dropping graded listing: %s", title[:60])
            graded_dropped += 1
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
            sale_date = datetime.now(timezone.utc).date()

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
                "source_url": resolved_url,
                "quantity": 1,
            }
        )

    logger.info(
        "PriceCharting: %d raw rows scanned → %d graded dropped → %d accepted.",
        counter + graded_dropped,
        graded_dropped,
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
    # Strip number suffix (e.g. "079/073") — the API searches by name only.
    search_name = _strip_card_number(card_name)
    params = {"q": f'name:"{search_name}"', "select": "id,name,tcgplayer,cardmarket"}

    logger.info("Falling back to pokemontcg.io for '%s' (search: '%s').", card_name, search_name)

    try:
        resp = _get(f"{url}?q=name%3A%22{requests.utils.quote(search_name)}%22&select=id,name,tcgplayer,cardmarket")
        data = resp.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("pokemontcg.io request failed: %s", exc)
        return []

    cards = data.get("data", [])
    if not cards:
        return []

    # Pick the card whose name best matches — not blindly cards[0].
    card = _best_card_match(cards, card_name) or cards[0]
    sales: list[dict[str, Any]] = []

    today = datetime.now(timezone.utc).date()

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
                        # Synthetic market price — not a completed sale.
                        "source_type": "market_estimate",
                        "quantity": 1,
                    }
                )

    logger.info("pokemontcg.io: synthesized %d price point(s) for '%s'.", len(sales), card_name)
    return sales


# ---------------------------------------------------------------------------
# PriceCharting price_data extractor (current market price from card page)
# ---------------------------------------------------------------------------


def _extract_pricecharting_price_data(
    soup: BeautifulSoup, card_name: str
) -> list[dict[str, Any]]:
    """Extract current NM price from the #price_data table on a card page.

    Used as a last resort when completed_auctions is JS-rendered. Returns a
    single synthetic record tagged 'pricecharting_static' so the analyzer can
    distinguish it from real sale history.
    """
    table = soup.find("table", {"id": "price_data"})
    if not table:
        return []

    # #used_price holds the ungraded (NM) market price.
    cell = table.find("td", {"id": "used_price"})
    if not cell:
        return []

    price_span = cell.find("span", class_="js-price")
    if not price_span:
        return []

    try:
        price = float(price_span.get_text(strip=True).replace("$", "").replace(",", ""))
    except ValueError:
        return []

    if price <= 0:
        return []

    today = datetime.now(timezone.utc).date()
    sale_id = "pc_static_" + hashlib.md5(f"{card_name}_{price}".encode()).hexdigest()[:8]

    logger.info("Extracted PriceCharting static price $%.2f for '%s'.", price, card_name)
    return [
        {
            "sale_id": sale_id,
            "price": round(price, 2),
            "date": today.isoformat(),
            "condition": "NM",
            "source": "pricecharting_static",
            # Current market snapshot, not a completed sale.
            "source_type": "market_estimate",
            "source_url": _PC_BASE,  # caller overwrites this with the resolved card URL
            "quantity": 1,
        }
    ]


# ---------------------------------------------------------------------------
# TCGPlayer price history via infinite-api + pokemontcg.io product ID lookup
# ---------------------------------------------------------------------------

_TCGPLAYER_INFINITE = "https://infinite-api.tcgplayer.com"
_POKEMONTCG_PRICES  = "https://prices.pokemontcg.io/tcgplayer"
_POKEMONTCG_API     = "https://api.pokemontcg.io/v2/cards"


def _lookup_tcgplayer_product_id(card_name: str) -> int | None:
    """Resolve a card name to a TCGPlayer product ID via pokemontcg.io.

    Flow:
      1. Query pokemontcg.io for the card (using name + optional number).
      2. Follow prices.pokemontcg.io redirect → tcgplayer.com/product/{id}.
      3. Extract the numeric product ID from the redirect Location header.

    Returns the product ID as int, or None on any failure.
    """
    search_name = _strip_card_number(card_name)

    # Build query: name + card number if present.
    query = f'name:"{search_name}"'
    number_match = re.search(r"(\d{3})/\d{3}", card_name)
    if number_match:
        query += f' number:{int(number_match.group(1))}'

    params = {"q": query, "select": "id,name,number,set,tcgplayer"}
    logger.info("Querying pokemontcg.io for product ID: %s", query)

    try:
        resp = _get(f"{_POKEMONTCG_API}?q={requests.utils.quote(query)}&select=id,name,number,set,tcgplayer")
        cards = resp.json().get("data", [])
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("pokemontcg.io lookup failed: %s", exc)
        return None

    card = _best_card_match(cards, card_name)
    if not card:
        logger.warning("No pokemontcg.io card found for '%s'.", card_name)
        return None

    card_id = card.get("id", "")

    # Check the permanent SQLite cache before hitting the slow redirect service.
    cached_pid = _product_id_cache_get(card_id)
    if cached_pid:
        logger.info("Product ID cache HIT: %s → %d", card_id, cached_pid)
        return cached_pid

    tcg_url = card.get("tcgplayer", {}).get("url", "")
    if not tcg_url:
        return None

    # prices.pokemontcg.io/tcgplayer/{card-id} → 302 → tcgplayer.com/product/{id}
    redirect_url = f"{_POKEMONTCG_PRICES}/{card_id}"
    logger.info("Following TCGPlayer redirect: %s", redirect_url)

    for attempt in range(2):  # one retry on timeout
        try:
            r = _http_session().get(
                redirect_url,
                headers={"User-Agent": random.choice(_USER_AGENTS)},
                timeout=(5, 12),
                allow_redirects=False,
            )
            location = r.headers.get("location", "")
            break
        except requests.RequestException as exc:
            logger.warning("TCGPlayer redirect attempt %d failed: %s", attempt + 1, exc)
            location = ""

    # Extract numeric product ID from "...product/223078" or "...u=https://tcgplayer.com/product/223078"
    match = re.search(r"/product/(\d+)", location)
    if not match:
        logger.warning("Could not extract product ID from redirect: %s", location)
        return None

    product_id = int(match.group(1))
    logger.info("Resolved TCGPlayer product ID: %d", product_id)
    _product_id_cache_put(card_id, product_id)   # cache permanently
    return product_id


def _fetch_tcgplayer_history(
    product_id: int, days: int = 30
) -> list[dict[str, Any]]:
    """Fetch daily price history from TCGPlayer's infinite-api.

    Returns one sale record per day that had actual transactions (quantity > 0),
    using averageSalesPrice as the price. Skips days with zero sales.

    Parameters
    ----------
    product_id : int
        TCGPlayer product ID.
    days : int
        Number of days of history to request (maps to range=month/year).

    Returns
    -------
    list[dict]
        Sale records, or empty list on failure.
    """
    range_param = "year" if days > 31 else "month"
    url = f"{_TCGPLAYER_INFINITE}/price/history/{product_id}?range={range_param}"
    logger.info("Fetching TCGPlayer history: %s", url)

    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "application/json",
        "Referer": "https://www.tcgplayer.com/",
    }

    try:
        resp = _http_session().get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("TCGPlayer history request failed: %s", exc)
        return []

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=days)
    sales: list[dict[str, Any]] = []
    counter = 0

    for entry in data.get("result", []):
        try:
            sale_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        except (ValueError, KeyError):
            continue

        if sale_date < cutoff:
            continue

        for variant in entry.get("variants", []):
            qty = int(variant.get("quantity", 0))
            if qty == 0:
                continue
            try:
                price = float(variant.get("averageSalesPrice", 0))
            except (ValueError, TypeError):
                continue
            if price <= 0:
                continue

            counter += 1
            sale_id = "tcp_" + hashlib.md5(
                f"{product_id}_{sale_date}_{variant.get('variant','')}_{counter}".encode()
            ).hexdigest()[:8]

            sales.append({
                "sale_id": sale_id,
                "price": round(price, 2),
                "date": sale_date.isoformat(),
                "condition": "NM",  # TCGPlayer averages mix conditions; tag as NM
                "source": "tcgplayer",
                # Not a completed sale — TCGPlayer's averageSalesPrice blends
                # conditions (LP/MP mixed in). Callers should weight these
                # records lower or surface a data-quality warning to users.
                "source_type": "market_estimate",
                "source_url": f"https://www.tcgplayer.com/product/{product_id}",
                "quantity": qty,
            })

    logger.info("TCGPlayer: %d sale-day records accepted for product %d.", len(sales), product_id)
    return sales


# ---------------------------------------------------------------------------
# eBay completed sales scraper
# ---------------------------------------------------------------------------

_EBAY_DATE_FORMATS = ["%b %d, %Y", "%d %b %Y", "%Y-%m-%d"]


def _scrape_ebay(card_name: str, days: int = 30) -> list[dict[str, Any]]:
    """Scrape eBay completed/sold listings for a Pokémon card.

    Uses the public eBay search with LH_Complete=1&LH_Sold=1 to get real
    individual sale records with prices and dates.

    Parameters
    ----------
    card_name : str
        Card name to search (set numbers like "079/073" are kept to improve
        precision).
    days : int
        Only include sales within this many calendar days.

    Returns
    -------
    list[dict]
        Sale records, or empty list on failure.
    """
    # Build a tight search query: card name + "pokemon" to avoid non-TCG hits.
    query = f"{card_name} pokemon"
    encoded = requests.utils.quote(query)
    url = (
        f"https://www.ebay.com/sch/i.html"
        f"?_nkw={encoded}&LH_Complete=1&LH_Sold=1&_sop=13"
    )

    logger.info("Scraping eBay completed sales: %s", url)

    try:
        resp = _get(url)
    except (requests.RequestException, ValueError) as exc:
        logger.error("eBay request failed: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    cutoff_date = datetime.now(timezone.utc).date() - timedelta(days=days)
    sales: list[dict[str, Any]] = []
    graded_dropped = 0
    counter = 0

    # eBay has used multiple container class names across DOM versions.
    # Try each in order so we degrade gracefully if they change again.
    items = (
        soup.find_all("li", class_="s-item")
        or soup.find_all("li", class_="s-card")
    )
    for item in items:
        # Title: prefer the dedicated title div (2024+), fall back to img alt.
        title_el = item.find("div", class_="s-item__title") or item.find("h3")
        if title_el:
            title = title_el.get_text(strip=True)
        else:
            img = item.find("img")
            title = img.get("alt", "").strip() if img else ""

        # Skip ads (eBay injects "Shop on eBay" promoted items).
        if not title or title.lower().startswith("shop on ebay"):
            continue

        # Drop graded cards.
        if _is_graded(title):
            graded_dropped += 1
            continue

        # --- Price ---
        # Try the semantic price element first (most reliable), then scan spans.
        price_el = item.find("span", class_="s-item__price")
        if price_el:
            # Handle "to" ranges like "$4.00 to $6.00" — take the lower bound.
            price_text = price_el.get_text(strip=True).split(" to ")[0].strip()
        else:
            price_text = ""
            for span in item.find_all("span"):
                text = span.get_text(strip=True)
                if re.match(r"^\$[\d,]+\.\d{2}$", text.replace(",", "")):
                    price_text = text
                    break

        if not price_text:
            continue

        try:
            price = float(price_text.replace("$", "").replace(",", ""))
        except ValueError:
            continue

        if price < 0.10 or price > 50_000:
            continue

        # --- Sold date ---
        sold_span = (
            item.find("span", class_="s-item__ended-date")
            or item.find("span", class_="s-item__time-end")
            or item.find("span", class_="su-styled-text")
        )
        date_text = sold_span.get_text(strip=True) if sold_span else ""
        # Format: "Sold  Apr 8, 2026" → strip prefix.
        date_text = re.sub(r"^[Ss]old\s+", "", date_text).strip()

        sale_date: date
        parsed = False
        for fmt in _EBAY_DATE_FORMATS:
            try:
                sale_date = datetime.strptime(date_text, fmt).date()
                parsed = True
                break
            except ValueError:
                continue
        if not parsed:
            sale_date = datetime.now(timezone.utc).date()

        if sale_date < cutoff_date:
            continue

        counter += 1
        condition = _parse_condition(title)
        sale_id_src = f"ebay_{card_name}_{sale_date}_{price}_{counter}"
        sale_id = "eb_" + hashlib.md5(sale_id_src.encode()).hexdigest()[:8]

        sales.append(
            {
                "sale_id": sale_id,
                "price": round(price, 2),
                "date": sale_date.isoformat(),
                "condition": condition,
                "source": "ebay",
                "source_url": url,
                "quantity": 1,
            }
        )

    logger.info(
        "eBay: %d items scanned → %d graded dropped → %d accepted.",
        counter + graded_dropped,
        graded_dropped,
        len(sales),
    )
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
    grade: str = "raw",
) -> list[dict[str, Any]] | dict[str, Any]:
    """Dispatcher. Routes to the registry path when HOLO_USE_REGISTRY=1,
    otherwise preserves the legacy linear scraper cascade.

    The registry path is behind a feature flag until the adapter coverage
    matches the legacy cascade and the parity test (H-1.10 Step 3) shows
    <5% distributional delta on canary cards.
    """
    import os as _os

    # Clear any prior-call audit so a legacy-path response never inherits
    # a stale registry audit from an earlier call in the same warm instance.
    from pokequant.sources import LAST_AUDIT as _LAST_AUDIT
    _LAST_AUDIT.set(None)

    if _os.environ.get("HOLO_USE_REGISTRY", "0") == "1":
        try:
            return _fetch_sales_via_registry(card_name, set_name=set_name,
                                             days=days, grade=grade, use_cache=use_cache)
        except Exception as exc:
            logger.warning("registry path failed, falling back to legacy: %s", exc)
    return _fetch_sales_legacy(card_name, set_name=set_name, days=days,
                               source=source, use_cache=use_cache, grade=grade)


def _fetch_sales_via_registry(
    card_name: str,
    *,
    set_name: str | None,
    days: int,
    grade: str,
    use_cache: bool,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Registry + reconciler path. Empty-result fallback to legacy is handled
    by the dispatcher's try/except."""
    from pokequant.sources import LAST_AUDIT, registry as _registry
    from pokequant.sources.reconciler import reconcile

    _registry.discover()
    records = _registry.fetch_all(card_name, days=days, grade=grade)
    if not records:
        # No active adapter returned records — don't bake an empty list into
        # the cache; dispatcher raises so legacy takes over.
        raise RuntimeError("registry returned zero records across all adapters")

    reconciled, audit = reconcile(records, days=days)
    LAST_AUDIT.set(audit)
    return [r.to_dict() for r in reconciled]


def _fetch_sales_legacy(
    card_name: str,
    set_name: str | None = None,
    days: int = 30,
    source: str = "pricecharting",
    use_cache: bool = True,
    grade: str = "raw",
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
    # Include days in the cache key so different time windows don't collide.
    cache_key_source = f"{source}_{grade}_{days}d"

    # --- L1 Cache (/tmp sqlite, warm-instance only) ---
    if use_cache:
        cached = _cache_get(card_slug, cache_key_source)
        if cached is not None:
            return cached

    # --- L2 Cache (Supabase, persistent cross-instance) ---
    # Only active when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set; the
    # module is a no-op otherwise. Any failure falls through silently to the
    # live-scrape path below. We only hit L2 for source="pricecharting"
    # because the scraper's multi-source merge (PC + eBay + TCGPlayer) is
    # handled live in this function; L2 stores the merged result.
    if use_cache and source == "pricecharting":
        try:
            from pokequant import supabase_cache as _l2
            if _l2.is_enabled():
                l2_sales = _l2.get_recent_sales(card_slug, grade, days)
                if l2_sales and len(l2_sales) >= 3:
                    logger.info("L2 Supabase HIT for '%s' — populating L1.", card_slug)
                    _cache_put(card_slug, cache_key_source, l2_sales)
                    return l2_sales
        except Exception as exc:
            # Supabase being unreachable must never block the request.
            logger.debug("L2 lookup failed, falling through: %s", exc)

    # --- Live fetch ---
    if source == "tcgapi":
        sales = _fetch_tcgapi(card_name, days=days)
    else:
        # 1. PriceCharting completed auctions — authoritative, grade-filtered.
        sales = _scrape_pricecharting(card_name, set_name=set_name, days=days, grade=grade)

        # 2. Supplement with eBay sold listings (raw grade only — eBay mixes grades
        #    and the _is_graded filter keyword-drops PSA/CGC/BGS titles, which is only
        #    correct when the user asked for raw data).
        if grade == "raw":
            try:
                ebay_supplement = _scrape_ebay(card_name, days=days)
                if ebay_supplement:
                    # Dedupe PC + eBay on (rounded price, date) — PC mirrors
                    # some eBay completed sales and counting them twice skews
                    # the median on low-volume days.
                    seen: set = {
                        (round(float(s.get("price", 0)), 2), str(s.get("date", ""))[:10])
                        for s in sales
                    }
                    deduped: list[dict[str, Any]] = []
                    for s in ebay_supplement:
                        key = (round(float(s.get("price", 0)), 2), str(s.get("date", ""))[:10])
                        if key in seen:
                            continue
                        seen.add(key)
                        deduped.append(s)
                    logger.info(
                        "Supplementing PC with %d eBay sales (%d dropped as dupes).",
                        len(deduped), len(ebay_supplement) - len(deduped),
                    )
                    sales = sales + deduped
            except Exception as exc:
                logger.warning("eBay supplement failed (continuing with PC-only): %s", exc)

        # 2b. For long time windows with sparse data, supplement with TCGPlayer
        #     even when PC/eBay returned some results — PriceCharting's visible
        #     table only covers ~30-50 recent sales regardless of the days param.
        #     Only for raw grade: TCGPlayer market prices blend grades, so
        #     supplementing a PSA 9/10 query would contaminate the comp.
        if days >= 90 and len(sales) < 15 and grade == "raw":
            logger.info(
                "Sparse data (%d sales) for %d-day window — supplementing with TCGPlayer.",
                len(sales), days,
            )
            try:
                product_id = _lookup_tcgplayer_product_id(card_name)
                if product_id:
                    tcg_sales = _fetch_tcgplayer_history(product_id, days=days)
                    if tcg_sales:
                        existing_dates = {s["date"] for s in sales}
                        new_tcg = [s for s in tcg_sales if s["date"] not in existing_dates]
                        sales = sales + new_tcg
                        logger.info(
                            "Added %d TCGPlayer records for sparse supplement.", len(new_tcg)
                        )
            except Exception as exc:
                logger.warning("TCGPlayer sparse supplement failed: %s", exc)

        if not sales:
            # Fallback: try TCGPlayer when PC and eBay both returned nothing.
            logger.info("No PC/eBay results — trying TCGPlayer.")
            product_id = _lookup_tcgplayer_product_id(card_name)
            if product_id:
                sales = _fetch_tcgplayer_history(product_id, days=days)

        # 3. Try PriceCharting static price_data (single current-price snapshot).
        if not sales:
            logger.info("All live sources failed — trying PriceCharting static price.")
            pc_url = _build_pricecharting_url(card_name, set_name)
            resolved_card_url = pc_url
            try:
                resp = _get(pc_url)
                static_soup = BeautifulSoup(resp.text, "html.parser")
                if not static_soup.find("table", {"id": "price_data"}):
                    card_url = _resolve_pricecharting_card_url(static_soup, card_name)
                    if card_url:
                        resolved_card_url = card_url
                        resp = _get(card_url)
                        static_soup = BeautifulSoup(resp.text, "html.parser")
                static_records = _extract_pricecharting_price_data(static_soup, card_name)
                # Patch source_url to the resolved card page.
                for r in static_records:
                    r["source_url"] = resolved_card_url
                sales = static_records
            except (requests.RequestException, ValueError):
                pass

        # 4. Last resort: pokemontcg.io synthetic price points.
        if not sales:
            logger.info("All primary sources failed — falling back to pokemontcg.io.")
            sales = _fetch_tcgapi(card_name, days=days)

    # --- Handle empty result ---
    if not sales:
        return {
            "error": f"No listings found for '{card_name}'",
            "card": card_name,
            "count": 0,
        }

    # --- Save to L1 cache (/tmp sqlite) ---
    _cache_put(card_slug, cache_key_source, sales)

    # --- Write-through to L2 (Supabase), fire-and-forget ---
    # Only for pricecharting source; that's the canonical merged feed.
    # Supabase module is a no-op when env vars are unset.
    if source == "pricecharting":
        try:
            from pokequant import supabase_cache as _l2
            _l2.put_sales(card_slug, grade, days, sales)
        except Exception as exc:
            logger.debug("L2 write-through skipped: %s", exc)

    return sales


def cache_get(card_slug: str, source: str) -> list[dict] | None:
    """Public interface to the SQLite cache. Returns payload or None on miss."""
    return _cache_get(card_slug, source)


def cache_put(card_slug: str, source: str, payload: list[dict]) -> None:
    """Public interface to write to the SQLite cache."""
    _cache_put(card_slug, source, payload)


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
