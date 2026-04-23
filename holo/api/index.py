"""
Vercel Python Serverless Function — Holo API

Single entry point that handles all /api routes:
  GET /api?action=price&card=Charizard+V
  GET /api?action=signal&card=Charizard+V
  GET /api?action=flip&card=Charizard+V&cost=4.50&method=pack
  GET /api?action=ev&set=Obsidian+Flames&retail=149.99
  GET /api?action=bulk&commons=500&uncommons=200
"""

from __future__ import annotations

import json
import os
import sys
import time
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Point cache to /tmp on Vercel (read-only filesystem outside /tmp).
os.environ.setdefault("HOLO_CACHE_DB", "/tmp/holo_cache.db")

# Add project root to path so pokequant imports work.
PROJECT_ROOT = str(Path(__file__).parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---- Module-level requests.Session for HTTP keep-alive -----------------------
# Reused across invocations on warm Vercel instances. Saves TCP+TLS handshake
# (~100–300ms) per outbound call to pokemontcg.io / PokeAPI etc.
_HTTP_SESSION = None
_HTTP_SESSION_LOCK = threading.Lock()


def _http_session():
    global _HTTP_SESSION
    if _HTTP_SESSION is None:
        with _HTTP_SESSION_LOCK:
            if _HTTP_SESSION is None:
                import requests as _requests
                from requests.adapters import HTTPAdapter
                s = _requests.Session()
                adapter = HTTPAdapter(pool_connections=16, pool_maxsize=32, max_retries=0)
                s.mount("https://", adapter)
                s.mount("http://", adapter)
                _HTTP_SESSION = s
    return _HTTP_SESSION


# ---- Tiny in-process memo for movers (survives warm invocations) -------------
_MEMO: dict[str, tuple[float, dict]] = {}
_MEMO_LOCK = threading.Lock()


def _memo_get(key: str, ttl: float):
    rec = _MEMO.get(key)
    if rec and (time.time() - rec[0]) < ttl:
        return rec[1]
    return None


def _memo_put(key: str, value: dict):
    with _MEMO_LOCK:
        _MEMO[key] = (time.time(), value)


# Cache-Control presets per action — tuned for staleness tolerance.
_CACHE_HEADERS = {
    "movers":  "public, max-age=300, s-maxage=600, stale-while-revalidate=1800",
    "meta":    "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800",
    "pokedex": "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800",
    "search":  "public, max-age=600, s-maxage=3600, stale-while-revalidate=21600",
    "history": "public, max-age=300, s-maxage=600, stale-while-revalidate=3600",
    "grades":  "public, max-age=300, s-maxage=600, stale-while-revalidate=3600",
    "sales":   "public, max-age=180, s-maxage=600, stale-while-revalidate=3600",
    "signal":  "public, max-age=180, s-maxage=600, stale-while-revalidate=1800",
    "price":   "public, max-age=180, s-maxage=600, stale-while-revalidate=1800",
}
_DEFAULT_CACHE = "s-maxage=300, stale-while-revalidate=600"


_PROD_ORIGINS = {
    "https://www.handoffpack.com",
    "https://handoffpack.com",
}


def _resolve_allowed_origin(request_origin: str) -> str | None:
    if not request_origin:
        return None
    if request_origin in _PROD_ORIGINS:
        return request_origin
    if request_origin.endswith(".vercel.app") and "handoffpack-www" in request_origin:
        return request_origin
    if os.environ.get("VERCEL_ENV") != "production" and request_origin.startswith("http://localhost"):
        return request_origin
    return None


def _json_response(handler, data: dict, status: int = 200, cache: str | None = None):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    origin = _resolve_allowed_origin(handler.headers.get("Origin", ""))
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Cache-Control", cache or _DEFAULT_CACHE)
    handler.end_headers()
    handler.wfile.write(json.dumps(data, default=str).encode())


# pokemontcg.io select= fieldsets. Rich for detail / pokedex, slim for search/list.
_META_FIELDS_FULL = (
    "id,name,number,images,set,rarity,tcgplayer,hp,types,subtypes,supertype,"
    "evolvesFrom,evolvesTo,abilities,attacks,weaknesses,resistances,"
    "retreatCost,convertedRetreatCost,flavorText,artist,"
    "nationalPokedexNumbers,regulationMark"
)
_META_FIELDS_SLIM = "id,name,number,images,set,rarity,tcgplayer"
_SEARCH_FIELDS = "id,name,number,images,set,rarity,supertype"


# Initialize the per-request sqlite cache schema + pragmas once per warm
# process. WAL + synchronous=NORMAL is the standard fast-read/fast-write combo
# for ephemeral caches on local disk (/tmp on Vercel).
_CACHE_INIT_DONE = False
_CACHE_INIT_LOCK = threading.Lock()


def _ensure_cache_schema():
    global _CACHE_INIT_DONE
    if _CACHE_INIT_DONE:
        return
    with _CACHE_INIT_LOCK:
        if _CACHE_INIT_DONE:
            return
        import sqlite3
        cache_db = os.environ.get("HOLO_CACHE_DB", "/tmp/holo_cache.db")
        try:
            with sqlite3.connect(cache_db) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA temp_store=MEMORY")
                conn.execute("""CREATE TABLE IF NOT EXISTS card_meta (
                    slug TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)""")
                conn.execute("""CREATE TABLE IF NOT EXISTS pokedex_cache (
                    dex_number INTEGER PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)""")
                conn.execute("""CREATE TABLE IF NOT EXISTS search_cache (
                    key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)""")
                conn.commit()
        except Exception:
            pass
        _CACHE_INIT_DONE = True


_ensure_cache_schema()


_SOURCE_LABELS = {
    "tcgplayer": "TCGPlayer",
    "ebay": "eBay",
    "pricecharting": "PriceCharting",
    "pricecharting_static": "PriceCharting",
    "pokemontcg.io": "pokemontcg.io",
}


def _shape_card_meta(best: dict, rich: bool = False) -> dict:
    """Shape a raw pokemontcg.io card dict into the payload we send over the
    wire. Shared by name-search and id-lookup paths so both produce the same
    object (important: the Pokédex overlay trusts this shape)."""
    set_obj = best.get("set", {}) or {}
    images = best.get("images", {}) or {}
    set_images = set_obj.get("images", {}) if isinstance(set_obj.get("images"), dict) else {}
    meta = {
        "id": best.get("id", ""),
        "name": best.get("name", ""),
        "number": best.get("number", ""),
        "image_small": images.get("small", ""),
        "image_large": images.get("large", ""),
        "set_name": set_obj.get("name", ""),
        "set_series": set_obj.get("series", ""),
        "set_symbol": set_images.get("symbol", ""),
        "set_logo": set_images.get("logo", ""),
        "rarity": best.get("rarity", ""),
        "release_date": set_obj.get("releaseDate", ""),
        "tcgplayer_url": (best.get("tcgplayer") or {}).get("url", ""),
        "set_printed_total": set_obj.get("printedTotal"),
        "set_total": set_obj.get("total"),
    }
    if rich:
        meta.update({
            "hp": best.get("hp", ""),
            "types": best.get("types", []) or [],
            "subtypes": best.get("subtypes", []) or [],
            "supertype": best.get("supertype", ""),
            "evolvesFrom": best.get("evolvesFrom", ""),
            "evolvesTo": best.get("evolvesTo", []) or [],
            "abilities": best.get("abilities", []) or [],
            "attacks": best.get("attacks", []) or [],
            "weaknesses": best.get("weaknesses", []) or [],
            "resistances": best.get("resistances", []) or [],
            "retreatCost": best.get("retreatCost", []) or [],
            "convertedRetreatCost": best.get("convertedRetreatCost"),
            "flavorText": best.get("flavorText", ""),
            "artist": best.get("artist", ""),
            "nationalPokedexNumbers": best.get("nationalPokedexNumbers", []) or [],
            "regulationMark": best.get("regulationMark", ""),
        })
    return meta


def _lookup_card_meta(card_name: str, rich: bool = False) -> dict:
    """Fetch card metadata (image, set, rarity, release date) from pokemontcg.io.

    Uses the name + optional number from the card query. Returns a dict with
    at minimum {image_small, image_large, set_name, rarity, number, release_date}
    or an empty dict if nothing found. Results are cached in /tmp via sqlite3.

    `rich=True` pulls extended TCG fields (attacks, abilities, pokedex numbers)
    used by /pokedex and /history detail views. Default is the slim payload used
    by list/card-grid callers — ~5x smaller JSON off pokemontcg.io.
    """
    import re as _re
    import sqlite3

    # Simple in-process cache keyed by slugified name.
    cache_db = os.environ.get("HOLO_CACHE_DB", "/tmp/holo_cache.db")
    slug = _re.sub(r"[^a-z0-9]+", "-", card_name.lower()).strip("-")
    # Separate cache rows for slim vs rich payloads so we never serve slim data
    # to a rich caller.
    cache_slug = slug if rich else f"{slug}::slim"
    try:
        with sqlite3.connect(cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS card_meta (
                    slug TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
            """)
            row = conn.execute(
                "SELECT payload FROM card_meta WHERE slug = ? AND fetched_at > datetime('now','-7 days')",
                (cache_slug,),
            ).fetchone()
            if row:
                return json.loads(row[0])
            # Rich callers can fall back to an existing slim cache hit for the
            # common fields while the rich fetch is in flight — but we still
            # need the rich fields, so only use this for slim callers.
            if not rich:
                pass
    except Exception:
        pass  # Cache miss is fine.

    # Strip trailing slash-numbers (e.g. "079/073"), capture optional loose number
    stripped = _re.sub(r"\s+\d{3}/\d{3,4}$", "", card_name).strip()
    number_match = _re.search(r"\b(\d{1,3})\b", stripped)
    target_number = number_match.group(1) if number_match else None
    query_name = _re.sub(r"\b\d{1,3}\b", "", stripped).strip()

    # pokemontcg.io number: is exact match but print numbers vary by variant.
    # Soft-match by name only, then rank results by name+number similarity.
    query = f'name:"{query_name}"'
    select = _META_FIELDS_FULL if rich else _META_FIELDS_SLIM
    sess = _http_session()
    headers = {"User-Agent": "Mozilla/5.0 Holo/1.0"}
    # Slim callers only need a handful of candidates to rank; pageSize=10 is
    # plenty and cuts pokemontcg.io response payloads roughly in half.
    page_size = 20 if rich else 10

    try:
        resp = sess.get(
            "https://api.pokemontcg.io/v2/cards",
            params={"q": query, "pageSize": page_size, "select": select},
            headers=headers,
            timeout=8,
        )
        resp.raise_for_status()
        cards = resp.json().get("data", [])
    except Exception:
        return {}

    if not cards:
        # Fallback: try without exact-match quotes (pokemontcg.io fuzzy search)
        try:
            resp = sess.get(
                "https://api.pokemontcg.io/v2/cards",
                params={"q": f"name:{query_name.split()[0]}*", "pageSize": page_size, "select": select},
                headers=headers,
                timeout=8,
            )
            resp.raise_for_status()
            cards = resp.json().get("data", [])
        except Exception:
            return {}

    if not cards:
        return {}

    # Rank: prefer exact-name match + exact-number match, then exact-name, then highest-number-proximity
    def _score(c: dict) -> int:
        score = 0
        if c.get("name", "").lower() == query_name.lower():
            score += 10
        if target_number and str(c.get("number", "")) == target_number:
            score += 20
        return score

    cards.sort(key=_score, reverse=True)
    best = cards[0]

    meta = _shape_card_meta(best, rich=rich)

    # Only cache non-empty results so transient API failures don't poison the cache.
    if meta.get("id"):
        try:
            with sqlite3.connect(cache_db) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO card_meta (slug, payload, fetched_at) VALUES (?, ?, datetime('now'))",
                    (cache_slug, json.dumps(meta)),
                )
                conn.commit()
        except Exception:
            pass

    return meta


def _lookup_pokedex_species(dex_number: int) -> dict:
    """Fetch species + pokemon data from PokeAPI, merged into one dict.

    Cached in sqlite (pokedex_cache table) with 30-day TTL. Returns {} on any
    failure so callers can degrade gracefully.
    """
    import sqlite3
    import urllib.request
    import urllib.error

    if not dex_number or dex_number <= 0:
        return {}

    cache_db = os.environ.get("HOLO_CACHE_DB", "/tmp/holo_cache.db")
    try:
        with sqlite3.connect(cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pokedex_cache (
                    dex_number INTEGER PRIMARY KEY,
                    payload TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
            """)
            row = conn.execute(
                "SELECT payload FROM pokedex_cache WHERE dex_number = ? AND fetched_at > datetime('now','-30 days')",
                (dex_number,),
            ).fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass

    def _fetch_json(url: str) -> dict:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Holo/1.0"})
        with urllib.request.urlopen(req, timeout=7) as resp:
            return json.loads(resp.read().decode("utf-8"))

    out: dict = {}

    try:
        species = _fetch_json(f"https://pokeapi.co/api/v2/pokemon-species/{dex_number}/")
    except Exception:
        species = None

    if species:
        # Latest English flavor text — iterate reversed so we pick most recent version.
        flavor_text = ""
        for entry in reversed(species.get("flavor_text_entries", []) or []):
            if (entry.get("language") or {}).get("name") == "en":
                flavor_text = (entry.get("flavor_text") or "").replace("\n", " ").replace("\f", " ").strip()
                if flavor_text:
                    break
        # English genus
        genus = ""
        for entry in species.get("genera", []) or []:
            if (entry.get("language") or {}).get("name") == "en":
                genus = entry.get("genus", "")
                break
        out.update({
            "name": species.get("name", ""),
            "genus": genus,
            "flavor_text": flavor_text,
            "habitat": (species.get("habitat") or {}).get("name") if species.get("habitat") else None,
            "color": (species.get("color") or {}).get("name") if species.get("color") else None,
            "generation": (species.get("generation") or {}).get("name") if species.get("generation") else None,
            "is_legendary": bool(species.get("is_legendary")),
            "is_mythical": bool(species.get("is_mythical")),
        })

    try:
        pkmn = _fetch_json(f"https://pokeapi.co/api/v2/pokemon/{dex_number}/")
    except Exception:
        pkmn = None

    if pkmn:
        stats_map: dict = {}
        for s in pkmn.get("stats", []) or []:
            name = (s.get("stat") or {}).get("name", "")
            val = s.get("base_stat", 0)
            if name:
                stats_map[name] = val
        sprites = pkmn.get("sprites", {}) or {}
        other = sprites.get("other", {}) or {}
        official = (other.get("official-artwork") or {}).get("front_default") if isinstance(other.get("official-artwork"), dict) else None
        sprite = official or sprites.get("front_default")
        try:
            height_m = float(pkmn.get("height", 0)) / 10.0
        except (TypeError, ValueError):
            height_m = 0.0
        try:
            weight_kg = float(pkmn.get("weight", 0)) / 10.0
        except (TypeError, ValueError):
            weight_kg = 0.0
        out.update({
            "height_m": height_m,
            "weight_kg": weight_kg,
            "types": [((t.get("type") or {}).get("name") or "") for t in (pkmn.get("types", []) or [])],
            "stats": {
                "hp": stats_map.get("hp", 0),
                "attack": stats_map.get("attack", 0),
                "defense": stats_map.get("defense", 0),
                "sp-atk": stats_map.get("special-attack", 0),
                "sp-def": stats_map.get("special-defense", 0),
                "speed": stats_map.get("speed", 0),
            },
            "sprite": sprite,
        })

    if out:
        try:
            with sqlite3.connect(cache_db) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO pokedex_cache (dex_number, payload, fetched_at) VALUES (?, ?, datetime('now'))",
                    (dex_number, json.dumps(out)),
                )
                conn.commit()
        except Exception:
            pass

    return out


def _lookup_card_by_id(card_id: str) -> dict:
    """Fetch the exact card by pokemontcg.io id (set-id + number).

    Bypasses name-based ranking so the Pokédex overlay renders the SAME
    printing the user is viewing — without this, "Miraidon ex" on a
    Paldean Fates page could resolve to the Scarlet & Violet base set
    printing and show a mismatched image/set in the overlay.
    """
    import hashlib
    import json
    import sqlite3

    cache_db = os.environ.get("HOLO_CACHE_DB", "/tmp/holo_cache.db")
    slug = f"byid:{hashlib.sha1(card_id.encode()).hexdigest()[:16]}"
    try:
        with sqlite3.connect(cache_db) as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS card_meta (
                slug TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)""")
            row = conn.execute(
                "SELECT payload FROM card_meta WHERE slug = ? AND fetched_at > datetime('now','-7 days')",
                (slug,),
            ).fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass

    try:
        resp = _http_session().get(
            f"https://api.pokemontcg.io/v2/cards/{card_id}",
            headers={"User-Agent": "Mozilla/5.0 Holo/1.0"},
            timeout=8,
        )
        if resp.status_code != 200:
            return {}
        best = (resp.json() or {}).get("data") or {}
    except Exception:
        return {}

    if not best.get("id"):
        return {}
    meta = _shape_card_meta(best, rich=True)
    try:
        with sqlite3.connect(cache_db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO card_meta (slug, payload, fetched_at) VALUES (?, ?, datetime('now'))",
                (slug, json.dumps(meta)),
            )
            conn.commit()
    except Exception:
        pass
    return meta


def _handle_pokedex(params: dict) -> dict:
    """Combined TCG metadata + PokeAPI species data for the Pokédex overlay.

    Prefers `id` (exact pokemontcg.io card id) over `card` (name) so the
    overlay matches the printing on screen. Falls back to name lookup.
    """
    card_id = params.get("id", [""])[0]
    card = params.get("card", [""])[0]
    if not card_id and not card:
        return {"error": "Missing 'id' or 'card' parameter"}
    meta: dict = {}
    if card_id:
        meta = _lookup_card_by_id(card_id)
    if not meta and card:
        meta = _lookup_card_meta(card, rich=True)
    if not meta:
        return {"error": "No card metadata found", "meta": {}, "species": {}}
    dex_numbers = meta.get("nationalPokedexNumbers") or []
    species: dict = {}
    if dex_numbers:
        try:
            species = _lookup_pokedex_species(int(dex_numbers[0]))
        except Exception:
            species = {}
    return {"meta": meta, "species": species}


def _extract_sources(records: list[dict]) -> list[dict]:
    """Build a deduped list of {label, url, count} for source attribution."""
    seen: dict[str, dict] = {}
    for r in records:
        src = r.get("source", "unknown")
        url = r.get("source_url", "")
        if src not in seen:
            seen[src] = {
                "name": src,
                "label": _SOURCE_LABELS.get(src, src),
                "url": url,
                "count": 0,
            }
        if not seen[src]["url"] and url:
            seen[src]["url"] = url
        seen[src]["count"] += 1
    return sorted(seen.values(), key=lambda s: s["count"], reverse=True)


def _handle_price(params: dict) -> dict:
    """Price check — decay-weighted market comp."""
    card = params.get("card", [""])[0]
    grade = params.get("grade", ["raw"])[0]
    if not card:
        return {"error": "Missing 'card' parameter"}

    from pokequant.scraper import fetch_sales
    from pokequant.comps.generator import generate_comp_from_list

    sales = fetch_sales(card_name=card, days=30, use_cache=True, grade=grade)
    if isinstance(sales, dict) and "error" in sales:
        return {"error": f"No market data found for '{card}'", "detail": sales.get("error")}
    if not isinstance(sales, list) or len(sales) == 0:
        return {"error": f"No sales found for '{card}'"}

    # 30-day window: take up to 25 most recent sales for the comp. Decay-weighting
    # still biases toward recent; older sales just expand the displayed window.
    result = generate_comp_from_list(sales=sales, card_id="web", card_name=card, n_sales=500)
    return {
        "card": card,
        "cmc": result.cmc,
        "mean": result.simple_mean,
        "delta_pct": result.cmc_vs_mean_pct,
        "confidence": result.confidence,
        "volatility": result.volatility_score,
        "stddev": result.price_stddev,
        "sales_used": result.sales_used,
        "newest": str(result.newest_sale_date.date()),
        "oldest": str(result.oldest_sale_date.date()),
        "insufficient_data_warning": result.insufficient_data_warning,
        "sources": _extract_sources(sales),
        "grade": grade,
        "meta": _lookup_card_meta(card),
    }


def _handle_signal(params: dict) -> dict:
    """Buy/Sell/Hold signal analysis."""
    card = params.get("card", [""])[0]
    grade = params.get("grade", ["raw"])[0]
    if not card:
        return {"error": "Missing 'card' parameter"}

    from pokequant.scraper import fetch_sales
    from pokequant.ingestion.normalizer import ingest_card
    from pokequant.signals.dip_detector import latest_signal

    sales = fetch_sales(card_name=card, days=30, use_cache=True, grade=grade)
    if isinstance(sales, dict) and "error" in sales:
        return {"error": f"No market data found for '{card}'", "signal": "UNKNOWN"}
    if not isinstance(sales, list) or len(sales) == 0:
        return {"error": "No sales found", "signal": "UNKNOWN"}
    if all(r.get("source") == "pokemontcg.io" for r in sales):
        return {"error": "Only synthetic data available — signal unreliable", "signal": "UNKNOWN"}

    card_record = {"card_id": "web", "name": card, "set": "Unknown", "sales": sales}
    df = ingest_card(card_record)
    result = latest_signal(df, card_id="web")

    return {
        "card": card,
        "signal": result.signal,
        "price": result.current_price,
        "sma7": result.sma_7,
        "sma30": result.sma_30,
        "dip_pct": result.price_vs_sma30_pct,
        "rsi": result.rsi,
        "vol_3d": result.volume_3d,
        "vol_surge_pct": result.volume_surge_pct,
        "sources": _extract_sources(sales),
        "grade": grade,
    }


def _handle_flip(params: dict) -> dict:
    """Flip profit calculator."""
    card = params.get("card", [""])[0]
    cost = params.get("cost", [""])[0]
    method = params.get("method", ["single"])[0]
    grade = params.get("grade", ["raw"])[0]

    if not card or not cost:
        return {"error": "Missing 'card' and/or 'cost' parameter"}

    try:
        raw_cost = float(cost)
    except ValueError:
        return {"error": f"Invalid cost: '{cost}'"}

    from config import DEFAULT_PACKS_PER_BOX

    # Parse packs (only meaningful for box method).
    packs_str = params.get("packs", [str(DEFAULT_PACKS_PER_BOX)])[0]
    try:
        packs = max(1, int(packs_str))
    except ValueError:
        packs = 36

    # Compute per-card cost basis based on acquisition method.
    # box:  user entered the total box price → divide by # of packs so each
    #       pull is evaluated at its proportional cost per pack.
    # pack: user entered the pack price → that is the full cost basis for the pull.
    # single: user entered the card price directly.
    if method == "box":
        cost_basis = round(raw_cost / packs, 4)
    else:
        cost_basis = raw_cost

    from pokequant.scraper import fetch_sales
    from pokequant.comps.generator import generate_comp_from_list
    from config import PLATFORM_FEE_RATE, SHIPPING_COST_BMWT, SHIPPING_COST_PWE, SHIPPING_VALUE_THRESHOLD, FLIP_THIN_MARGIN_THRESHOLD_PCT

    sales = fetch_sales(card_name=card, days=30, use_cache=True, grade=grade)
    if isinstance(sales, dict) and "error" in sales:
        return {"error": f"No market data found for '{card}'"}
    if not isinstance(sales, list) or len(sales) == 0:
        return {"error": f"No sales found for '{card}'"}

    # Data-quality flags. `synthetic_only` kept for API compat (true when
    # 100% of data is synthetic pokemontcg.io fallback). `synthetic_ratio`
    # is the richer signal: TCGPlayer market estimates, PC static snapshots,
    # and pokemontcg.io fallbacks all count as non-sale records. A flip
    # verdict based on >30% market-estimate data should be treated with
    # caution — these are condition-blended prices, not completed sales.
    synthetic_only = all(r.get("source") == "pokemontcg.io" for r in sales)
    synthetic_count = sum(1 for r in sales if r.get("source_type") == "market_estimate")
    synthetic_ratio = round(synthetic_count / len(sales), 3) if sales else 0.0

    comp = generate_comp_from_list(sales=sales, card_id="flip", card_name=card, n_sales=500)
    market_value = comp.cmc

    platform_fee = round(market_value * PLATFORM_FEE_RATE, 2)
    shipping_cost = SHIPPING_COST_BMWT if market_value >= SHIPPING_VALUE_THRESHOLD else SHIPPING_COST_PWE
    shipping_type = "BMWT" if market_value >= SHIPPING_VALUE_THRESHOLD else "PWE"
    net_revenue = round(market_value - platform_fee - shipping_cost, 2)
    profit = round(net_revenue - cost_basis, 2)
    # Return on cost basis (ROI), not gross margin on revenue — a flipper cares
    # about what they make per dollar they put in. Field name kept for API compat.
    margin_pct = round((profit / cost_basis) * 100, 1) if cost_basis > 0 else 0.0

    if profit <= 0:
        verdict = "DO NOT SELL"
    elif margin_pct < FLIP_THIN_MARGIN_THRESHOLD_PCT:
        verdict = "HOLD"
    else:
        verdict = "FLIP IT"

    # Break-even price: what the card would need to sell for to recoup costs + fees + shipping.
    # Solve: break_even * (1 - fee_rate) - shipping = cost_basis
    from config import PLATFORM_FEE_RATE as _FEE
    break_even = round((cost_basis + shipping_cost) / (1 - _FEE), 2) if (1 - _FEE) > 0 else 0.0
    # If break-even falls below the shipping tier threshold while we priced
    # with BMWT, the real sale at that price would ship PWE ($1), not BMWT
    # ($4). Recompute once with PWE so break-even isn't overstated. Can't
    # ping-pong because PWE ≤ BMWT.
    if break_even < SHIPPING_VALUE_THRESHOLD and shipping_cost == SHIPPING_COST_BMWT:
        shipping_cost = SHIPPING_COST_PWE
        break_even = round((cost_basis + shipping_cost) / (1 - _FEE), 2) if (1 - _FEE) > 0 else 0.0

    return {
        "card": card,
        "method": method,
        "raw_cost": raw_cost,
        "packs": packs if method == "box" else None,
        "cmc": market_value,
        "cost_basis": round(cost_basis, 2),
        "platform_fee": platform_fee,
        "shipping_cost": shipping_cost,
        "shipping_type": shipping_type,
        "net_revenue": net_revenue,
        "profit": profit,
        "margin_pct": margin_pct,
        "verdict": verdict,
        "break_even": break_even,
        "confidence": comp.confidence,
        "sales_used": comp.sales_used,
        "synthetic_only": synthetic_only,
        "synthetic_ratio": synthetic_ratio,
        "data_quality_warning": (
            f"{int(synthetic_ratio * 100)}% of data is market estimate, "
            "not completed sales — verdict is a best-effort estimate."
            if synthetic_ratio > 0.3 else None
        ),
        "sources": _extract_sources(sales),
        "grade": grade,
    }


def _handle_ev(params: dict) -> dict:
    """Sealed box EV calculator."""
    set_name = params.get("set", [""])[0]
    retail = params.get("retail", [""])[0]

    if not set_name or not retail:
        return {"error": "Missing 'set' and/or 'retail' parameter"}

    try:
        retail_price = float(retail)
    except ValueError:
        return {"error": f"Invalid retail price: '{retail}'"}

    # Use the existing analyze.py helpers for EV.
    from pokequant.analyze import _fetch_set_cards, _build_top3_tier_data
    from pokequant.ev.calculator import calculate_box_ev
    from config import DEFAULT_PACKS_PER_BOX as _DEFAULT_PACKS

    packs_per_box = int(params.get("packs", [str(_DEFAULT_PACKS)])[0])
    cards = _fetch_set_cards(set_name)
    if not cards:
        return {"error": f"Could not find set '{set_name}'"}

    pull_rates = _build_top3_tier_data(cards, packs_per_box)
    if not pull_rates:
        return {"error": f"No pull rate data for '{set_name}'"}

    box_data = {
        "set_name": set_name,
        "packs_per_box": packs_per_box,
        "retail_price": retail_price,
        "pull_rates": pull_rates,
    }
    result = calculate_box_ev(box_data)

    return {
        "set": result.set_name,
        "ev": round(result.total_ev, 2),
        "retail": result.retail_price,
        "delta": round(result.ev_vs_retail, 2),
        "delta_pct": round(result.ev_vs_retail_pct, 1),
        "rec": result.recommendation,
        "tiers": len(result.tier_breakdown),
        "cards_sampled": len(cards),
    }


def _handle_bulk(params: dict) -> dict:
    """Bulk liquidation optimizer."""
    from pokequant.bulk.optimizer import analyze_bulk_lot

    inventory = {}
    if params.get("commons"):
        inventory["Common"] = int(params["commons"][0])
    if params.get("uncommons"):
        inventory["Uncommon"] = int(params["uncommons"][0])
    if params.get("revholos"):
        inventory["Reverse Holo"] = int(params["revholos"][0])
    if params.get("holorares"):
        inventory["Holo Rare"] = int(params["holorares"][0])
    if params.get("ultrarares"):
        inventory["Ultra Rare"] = int(params["ultrarares"][0])

    if not inventory:
        return {"error": "No inventory provided"}

    result = analyze_bulk_lot(inventory)
    return {
        "net": round(result.net_profit, 2),
        "gross": round(result.gross_payout, 2),
        "shipping": round(result.shipping_cost, 2),
        "cards": result.total_cards,
        "liquidate": result.should_liquidate,
        "recommendation": result.recommendation,
    }


def _handle_history(params: dict) -> dict:
    """Historical daily price series for the sparkline chart.

    Returns a list of {date, price, count} points bucketed by day,
    using the median daily price (robust to outliers).
    """
    card = params.get("card", [""])[0]
    grade = params.get("grade", ["raw"])[0]
    days_str = params.get("days", ["90"])[0]
    try:
        days = max(7, min(365, int(days_str)))
    except ValueError:
        days = 90

    if not card:
        return {"error": "Missing 'card' parameter"}

    from pokequant.scraper import fetch_sales
    import statistics
    from collections import defaultdict
    from datetime import date, timedelta

    sales = fetch_sales(card_name=card, days=days, use_cache=True, grade=grade)
    if isinstance(sales, dict) and "error" in sales:
        return {"error": f"No market data found for '{card}'"}
    if not isinstance(sales, list) or len(sales) == 0:
        return {"error": f"No sales found for '{card}'"}

    # Collect raw prices so we can compute a robust outlier floor before bucketing.
    # Low-value junk listings (lot sales, proxies, damaged cards) can drop the low
    # to pennies on a $500 card, which makes the HIGH/LOW band useless. Drop any
    # price that's less than 15% of the overall median — this is conservative
    # enough to keep legitimate dips but cuts out obvious garbage.
    raw_prices: list[float] = []
    for s in sales:
        try:
            p = float(s["price"])
            if p > 0:
                raw_prices.append(p)
        except (ValueError, TypeError):
            continue

    if not raw_prices:
        return {"error": "No valid price data"}

    overall_median = statistics.median(raw_prices)
    outlier_floor = overall_median * 0.15

    # Bucket by day, median price per day
    buckets: dict[str, list[float]] = defaultdict(list)
    for s in sales:
        try:
            d = str(s["date"])[:10]
            p = float(s["price"])
            if p >= outlier_floor:
                buckets[d].append(p)
        except (KeyError, ValueError, TypeError):
            continue

    if not buckets:
        return {"error": "No valid price data"}

    # Hard-clamp to the requested window so the chart always matches the tab.
    cutoff = date.today() - timedelta(days=days)
    sorted_dates = sorted(d for d in buckets.keys() if date.fromisoformat(d) >= cutoff)
    if not sorted_dates:
        return {"error": "No valid price data in selected range"}

    earliest = date.fromisoformat(sorted_dates[0])
    today = date.today()
    points = []
    last_price = None
    d = earliest
    while d <= today:
        key = d.isoformat()
        if key in buckets:
            last_price = statistics.median(buckets[key])
            count = len(buckets[key])
        else:
            count = 0
        if last_price is not None:
            points.append({"date": key, "price": round(last_price, 2), "count": count})
        d += timedelta(days=1)

    if not points:
        return {"error": "No chart data"}

    first_price = points[0]["price"]
    last = points[-1]["price"]
    high = max(p["price"] for p in points)
    low = min(p["price"] for p in points)
    change = round(last - first_price, 2)
    change_pct = round((last / first_price - 1) * 100, 2) if first_price > 0 else 0.0

    # Data-quality flags — expose ratio of market-estimate records (TCGPlayer
    # averages, PC static snapshots, pokemontcg.io synth) vs completed sales
    # so the UI can show a caveat when the chart is mostly estimates.
    synthetic_count = sum(1 for r in sales if r.get("source_type") == "market_estimate")
    synthetic_ratio = round(synthetic_count / len(sales), 3) if sales else 0.0

    return {
        "card": card,
        "grade": grade,
        "days": days,
        "points": points,
        "summary": {
            "current": last,
            "first": first_price,
            "high": high,
            "low": low,
            "change": change,
            "change_pct": change_pct,
            "sales_count": len(sales),
        },
        "synthetic_ratio": synthetic_ratio,
        "data_quality_warning": (
            f"{int(synthetic_ratio * 100)}% of data is market estimate, not completed sales."
            if synthetic_ratio > 0.3 else None
        ),
        "sources": _extract_sources(sales),
        "meta": _lookup_card_meta(card),
    }


def _handle_sales(params: dict) -> dict:
    """Recent sold listings feed — 130point style."""
    card = params.get("card", [""])[0]
    grade = params.get("grade", ["raw"])[0]
    limit_str = params.get("limit", ["25"])[0]
    try:
        limit = max(5, min(100, int(limit_str)))
    except ValueError:
        limit = 25

    if not card:
        return {"error": "Missing 'card' parameter"}

    from pokequant.scraper import fetch_sales

    sales = fetch_sales(card_name=card, days=30, use_cache=True, grade=grade)
    if isinstance(sales, dict) and "error" in sales:
        return {"error": f"No market data found for '{card}'"}
    if not isinstance(sales, list) or len(sales) == 0:
        return {"error": f"No sales found for '{card}'"}

    # Sort by date descending, take top N.
    sorted_sales = sorted(sales, key=lambda s: str(s.get("date", "")), reverse=True)[:limit]

    feed = [
        {
            "date": str(s.get("date", ""))[:10],
            "price": float(s.get("price", 0)),
            "condition": s.get("condition", "NM"),
            "source": s.get("source", "unknown"),
            "source_label": _SOURCE_LABELS.get(s.get("source", ""), s.get("source", "")),
            "source_url": s.get("source_url", ""),
        }
        for s in sorted_sales
    ]

    return {
        "card": card,
        "grade": grade,
        "count": len(feed),
        "sales": feed,
        "total_available": len(sales),
    }


def _handle_grade_roi(params: dict) -> dict:
    """Expected-value math for grading a raw card.

    Formula:
      gross_10 = psa10_price * p10 * (1 - sell_fees)
      gross_9  = psa9_price  * p9  * (1 - sell_fees)
      gross_sub = est_raw_price * p_sub * (1 - sell_fees)  # sub/ungradeable returned as raw
      ev = gross_10 + gross_9 + gross_sub - grading_cost - shipping
      delta = ev - raw_price  (i.e. keep-and-sell-raw is the baseline)

    Default probabilities reflect "lightly played to near-mint raw card, pulled from
    pack and sleeved promptly". User can override via ?p10=0.40&p9=0.40&p_sub=0.20 etc.

    Grading services default to PSA Value (~$25/card) unless ?service= specified.
    """
    card = params.get("card", [""])[0]
    if not card:
        return {"error": "Missing 'card' parameter"}

    # User overrides
    def _fl(name: str, default: float) -> float:
        try:
            return float(params.get(name, [str(default)])[0])
        except (ValueError, TypeError):
            return default

    service = params.get("service", ["psa_value"])[0]

    # Service cost + typical turnaround (per-card, USD) — approximate, 2026 rates
    services = {
        "psa_value":    {"label": "PSA Value",     "cost": 25.0, "turnaround": "45 days"},
        "psa_regular":  {"label": "PSA Regular",   "cost": 75.0, "turnaround": "10 days"},
        "psa_express":  {"label": "PSA Express",  "cost": 150.0, "turnaround": "5 days"},
        "cgc_standard": {"label": "CGC Standard",  "cost": 18.0, "turnaround": "30 days"},
        "cgc_express":  {"label": "CGC Express",   "cost": 35.0, "turnaround": "7 days"},
        "tag_grading":  {"label": "TAG Grading",   "cost": 20.0, "turnaround": "20 days"},
    }
    svc = services.get(service, services["psa_value"])

    p10 = _fl("p10", 0.35)   # modern-era NM raw → PSA 10 rate is typically 30-40%
    p9  = _fl("p9",  0.45)   # 40-50% land at PSA 9
    p_sub = _fl("p_sub", 1.0 - p10 - p9)  # remainder come back sub-grade
    if p_sub < 0:
        p_sub = 0.0

    grading_cost = _fl("cost", svc["cost"])
    shipping = _fl("shipping", 5.0)  # round-trip shipping per card
    sell_fees = _fl("fees", 0.13)  # combined seller platform fees

    # Fetch all three grades for the card
    from pokequant.scraper import fetch_sales
    from pokequant.comps.generator import generate_comp_from_list

    prices = {}
    for g in ("raw", "psa9", "psa10"):
        try:
            s = fetch_sales(card_name=card, days=30, use_cache=True, grade=g)
            if isinstance(s, list) and s:
                comp = generate_comp_from_list(sales=s, card_id=f"roi_{g}", card_name=card, n_sales=500)
                prices[g] = {"cmc": comp.cmc, "sales_used": comp.sales_used, "confidence": comp.confidence}
        except Exception:
            prices[g] = None

    raw_price = (prices.get("raw") or {}).get("cmc") or 0.0
    psa9_price = (prices.get("psa9") or {}).get("cmc") or 0.0
    psa10_price = (prices.get("psa10") or {}).get("cmc") or 0.0

    if raw_price <= 0:
        return {"error": "Could not determine raw price — grading EV requires a raw comp."}
    if psa10_price <= 0:
        return {"error": "Could not determine PSA 10 price — no graded comps found."}

    # Expected gross revenue from grading
    gross_10 = psa10_price * p10 * (1 - sell_fees)
    gross_9 = psa9_price * p9 * (1 - sell_fees) if psa9_price > 0 else 0.0
    gross_sub = raw_price * p_sub * (1 - sell_fees)

    expected_revenue = round(gross_10 + gross_9 + gross_sub, 2)
    total_cost = round(grading_cost + shipping, 2)
    net_ev = round(expected_revenue - total_cost, 2)
    raw_baseline = round(raw_price * (1 - sell_fees), 2)  # selling raw also has fees
    delta = round(net_ev - raw_baseline, 2)
    delta_pct = round((delta / raw_baseline) * 100, 1) if raw_baseline > 0 else 0.0

    # Verdict: delta >= $10 AND delta_pct >= 20% → GRADE IT
    if delta >= 10 and delta_pct >= 20:
        verdict = "GRADE IT"
        verdict_tone = "buy"
        rationale = (
            f"Grading adds ~{money_fmt(delta)} ({delta_pct:+.0f}%) over selling raw. "
            f"Expected grade premium justifies the ${grading_cost:.0f} fee + {svc['turnaround']} wait."
        )
    elif delta >= -5:
        verdict = "BORDERLINE"
        verdict_tone = "neutral"
        rationale = (
            f"Net EV is only {money_fmt(delta)} over raw. "
            f"Grade if you expect PSA 10 rate > {p10 * 100:.0f}% (centering/edges look exceptional)."
        )
    else:
        verdict = "SELL RAW"
        verdict_tone = "sell"
        rationale = (
            f"Grading loses ~{money_fmt(abs(delta))} in expected value. "
            f"Raw comp is strong relative to graded — move it as-is."
        )

    return {
        "card": card,
        "service": svc["label"],
        "service_cost": grading_cost,
        "turnaround": svc["turnaround"],
        "prices": prices,
        "assumptions": {
            "p10": p10,
            "p9": p9,
            "p_sub": p_sub,
            "sell_fees": sell_fees,
            "shipping": shipping,
        },
        "breakdown": {
            "expected_psa10_value": round(gross_10, 2),
            "expected_psa9_value": round(gross_9, 2),
            "expected_sub_value": round(gross_sub, 2),
            "expected_revenue": expected_revenue,
            "total_cost": total_cost,
            "net_ev": net_ev,
            "raw_baseline": raw_baseline,
            "delta": delta,
            "delta_pct": delta_pct,
        },
        "verdict": verdict,
        "verdict_tone": verdict_tone,
        "rationale": rationale,
    }


def money_fmt(n: float) -> str:
    sign = "+" if n >= 0 else "-"
    return f"{sign}${abs(n):.2f}"


def _handle_grades(params: dict) -> dict:
    """Side-by-side comparison of Raw / PSA 9 / PSA 10 prices for a single card."""
    card = params.get("card", [""])[0]
    if not card:
        return {"error": "Missing 'card' parameter"}

    from pokequant.scraper import fetch_sales
    from pokequant.comps.generator import generate_comp_from_list

    out = {"card": card, "grades": {}}
    for grade in ("raw", "psa9", "psa10"):
        try:
            sales = fetch_sales(card_name=card, days=30, use_cache=True, grade=grade)
            if isinstance(sales, list) and sales:
                comp = generate_comp_from_list(
                    sales=sales, card_id=f"grade_{grade}", card_name=card, n_sales=500,
                )
                out["grades"][grade] = {
                    "cmc": comp.cmc,
                    "mean": comp.simple_mean,
                    "sales_used": comp.sales_used,
                    "confidence": comp.confidence,
                    "oldest": str(comp.oldest_sale_date.date()),
                    "newest": str(comp.newest_sale_date.date()),
                }
            else:
                out["grades"][grade] = None
        except Exception as exc:
            out["grades"][grade] = {"error": str(exc)}
    return out


def _handle_meta(params: dict) -> dict:
    """Lightweight card metadata lookup — name, image, set info.

    Used by the frontend carousel to fetch card thumbnails without
    pulling a full price history. Results share the pokemontcg.io
    SQLite cache (7-day TTL) with the history endpoint.
    """
    card = params.get("card", [""])[0]
    if not card:
        return {"error": "Missing 'card' parameter"}
    meta = _lookup_card_meta(card)
    if not meta:
        return {"error": f"No card metadata found for '{card}'"}
    return {"card": card, "meta": meta}


# Universe of cards to evaluate when computing top movers. Kept small so the
# handler stays under the 60s Vercel maxDuration even on a cold cache.
_MOVERS_UNIVERSE: list[str] = [
    "Umbreon ex 161",
    "Pikachu ex 232",
    "Gardevoir ex 245",
    "Charizard ex 199",
    "Iono 237",
    "Miraidon ex 243",
    "Lugia V 138",
    "Latias ex 239",
    "Charizard V 154",
    "Giratina V 186",
    "Mew VMAX 114",
    "Rayquaza VMAX 111",
]


def _handle_movers(params: dict) -> dict:
    """Top movers — cards ranked by biggest 7-day price change.

    Evaluates a curated universe of popular cards, fetches a short history
    for each, and returns them sorted by |change_pct|. Direction (up/down)
    is preserved so the frontend can show gainers vs losers.

    Query params:
      ?limit=8        — max cards to return (default 8, max 20)
      ?window=7       — days to measure change over (default 7, max 30)
    """
    import statistics
    from collections import defaultdict
    from concurrent.futures import ThreadPoolExecutor
    from pokequant.scraper import fetch_sales

    try:
        limit = max(1, min(20, int(params.get("limit", ["8"])[0])))
    except ValueError:
        limit = 8
    try:
        window = max(3, min(30, int(params.get("window", ["7"])[0])))
    except ValueError:
        window = 7

    # Server-side memoization — movers is the home-page marquee and repeats
    # across every visitor. 10-min TTL on the full payload.
    memo_key = f"movers::{window}::{limit}"
    cached = _memo_get(memo_key, ttl=600)
    if cached is not None:
        return cached

    def _one(name: str) -> dict | None:
        try:
            sales = fetch_sales(card_name=name, days=window, use_cache=True, grade="raw")
            if not isinstance(sales, list) or len(sales) < 2:
                return None

            raw_prices = [float(s["price"]) for s in sales
                          if float(s.get("price", 0)) > 0]
            if len(raw_prices) < 2:
                return None
            # Percentage-of-median floor is only reliable once we have enough
            # samples that the median itself isn't an outlier. Below 5 sales a
            # single junk listing can drag the median down and let other junk
            # through. Fall back to the absolute hard floor from config.
            from config import HARD_PRICE_FLOOR
            if len(raw_prices) >= 5:
                floor = statistics.median(raw_prices) * 0.15
            else:
                floor = HARD_PRICE_FLOOR

            buckets: dict[str, list[float]] = defaultdict(list)
            for s in sales:
                try:
                    p = float(s["price"])
                    if p >= floor:
                        buckets[str(s["date"])[:10]].append(p)
                except (KeyError, ValueError, TypeError):
                    continue

            if len(buckets) < 2:
                return None

            sorted_dates = sorted(buckets.keys())
            first_price = statistics.median(buckets[sorted_dates[0]])
            last_price = statistics.median(buckets[sorted_dates[-1]])
            if first_price <= 0:
                return None

            change_pct = round((last_price / first_price - 1) * 100, 2)
            meta = _lookup_card_meta(name)

            return {
                "card": name,
                "current": round(last_price, 2),
                "change_pct": change_pct,
                "direction": "up" if change_pct >= 0 else "down",
                "sales_count": len(sales),
                "image_small": meta.get("image_small", "") if meta else "",
                "name": meta.get("name", name) if meta else name,
                "number": meta.get("number", "") if meta else "",
            }
        except Exception:
            return None  # One card failing shouldn't tank the whole list.

    # Parallel fan-out: each card hits fetch_sales independently. The sqlite
    # cache layer uses short-lived per-call connections, so concurrent reads
    # are safe; writes are rare (24h TTL) and serialized by sqlite itself.
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_one, _MOVERS_UNIVERSE))
    movers: list[dict] = [m for m in results if m is not None]

    # Sort by absolute % change descending — biggest movers first.
    movers.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
    payload = {
        "window_days": window,
        "count": min(len(movers), limit),
        "movers": movers[:limit],
    }
    _memo_put(memo_key, payload)
    return payload


def _handle_search(params: dict) -> dict:
    """Type-ahead card search backed by pokemontcg.io.

    GET /api?action=search&q=<query>&limit=12

    Returns a lightweight list of card match objects so the frontend can show
    a disambiguation dropdown. Cached in sqlite (`search_cache`) for 6 hours
    keyed by (normalized query, limit).
    """
    import hashlib
    import re as _re
    import sqlite3

    raw_q = params.get("q", [""])[0] or ""
    q = raw_q.strip()
    try:
        limit = max(1, min(24, int(params.get("limit", ["12"])[0])))
    except ValueError:
        limit = 12

    if len(q) < 2:
        return {"results": []}

    cache_db = os.environ.get("HOLO_CACHE_DB", "/tmp/holo_cache.db")
    key = hashlib.sha1(f"{q.lower()}|{limit}".encode()).hexdigest()

    # Cache read.
    try:
        with sqlite3.connect(cache_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    fetched_at TEXT NOT NULL
                )
            """)
            row = conn.execute(
                "SELECT payload FROM search_cache WHERE key = ? AND fetched_at > datetime('now','-6 hours')",
                (key,),
            ).fetchone()
            if row:
                return json.loads(row[0])
    except Exception:
        pass

    # Split into name + optional trailing number token.
    m = _re.match(r"^(.*?)[\s]+(\d{1,4})$", q)
    if m:
        name_part = m.group(1).strip()
        number_part = m.group(2)
    else:
        name_part = q
        number_part = None

    if not name_part:
        return {"results": []}

    # pokemontcg.io Lucene-ish query: prefix wildcard on name.
    # Escape quotes defensively.
    safe_name = name_part.replace('"', '').replace('\\', '')
    query_str = f'name:"{safe_name}*"'

    try:
        resp = _http_session().get(
            "https://api.pokemontcg.io/v2/cards",
            params={
                "q": query_str,
                "pageSize": min(25, max(limit * 2, 16)),
                "select": _SEARCH_FIELDS,
            },
            headers={"User-Agent": "Mozilla/5.0 Holo/1.0"},
            timeout=8,
        )
        resp.raise_for_status()
        cards = resp.json().get("data", []) or []
    except Exception:
        return {"results": [], "error": "search_unavailable"}

    lc_name = name_part.lower()

    def _rank(c: dict) -> tuple:
        cname = (c.get("name") or "").lower()
        cnum = str(c.get("number") or "")
        release = ((c.get("set") or {}).get("releaseDate") or "") or ""
        # Primary: exact-number match floats to top when user typed a number.
        num_score = 2 if (number_part and cnum == number_part) else 0
        # Name-match tiers.
        if cname == lc_name:
            name_score = 3
        elif cname.startswith(lc_name):
            name_score = 2
        elif lc_name in cname:
            name_score = 1
        else:
            name_score = 0
        # Sort descending: higher score first; newer release_date first.
        return (-num_score, -name_score, _negate_date(release))

    def _negate_date(d: str) -> str:
        # Lexicographic trick: invert so newer dates sort first.
        # pokemontcg.io uses YYYY/MM/DD format.
        if not d:
            return "0000/00/00"
        # Build a reverse-sortable key by subtracting from 9999.
        try:
            parts = d.split("/")
            y = 9999 - int(parts[0])
            mo = 99 - int(parts[1]) if len(parts) > 1 else 0
            da = 99 - int(parts[2]) if len(parts) > 2 else 0
            return f"{y:04d}/{mo:02d}/{da:02d}"
        except Exception:
            return "9999/99/99"

    cards.sort(key=_rank)

    seen: set = set()
    results: list[dict] = []
    for c in cards:
        nm = c.get("name", "") or ""
        num = str(c.get("number", "") or "")
        set_obj = c.get("set", {}) or {}
        set_name = set_obj.get("name", "") or ""
        triple = (nm.lower(), num, set_name.lower())
        if triple in seen:
            continue
        seen.add(triple)
        images = c.get("images", {}) or {}
        release_date = set_obj.get("releaseDate", "") or ""
        release_year = 0
        try:
            release_year = int(release_date.split("/")[0]) if release_date else 0
        except Exception:
            release_year = 0
        results.append({
            "id": c.get("id", "") or "",
            "name": nm,
            "number": num,
            "set_name": set_name,
            "set_series": set_obj.get("series", "") or "",
            "release_date": release_date,
            "release_year": release_year,
            "image_small": images.get("small", "") or "",
            "rarity": c.get("rarity", "") or "",
            "supertype": c.get("supertype", "") or "",
        })
        if len(results) >= limit:
            break

    payload = {"results": results}
    # Only cache successful payloads — if the upstream search errored we must
    # not poison the 6-hour cache (otherwise a transient pokemontcg.io blip
    # gives every user empty typeahead for hours).
    if "error" not in payload:
        try:
            with sqlite3.connect(cache_db) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO search_cache (key, payload, fetched_at) VALUES (?, ?, datetime('now'))",
                    (key, json.dumps(payload)),
                )
                conn.commit()
        except Exception:
            pass

    return payload


_HANDLERS = {
    "price": _handle_price,
    "signal": _handle_signal,
    "flip": _handle_flip,
    "ev": _handle_ev,
    "bulk": _handle_bulk,
    "history": _handle_history,
    "grades": _handle_grades,
    "sales": _handle_sales,
    "gradeit": _handle_grade_roi,
    "meta": _handle_meta,
    "movers": _handle_movers,
    "pokedex": _handle_pokedex,
    "search": _handle_search,
}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        action = params.get("action", [""])[0]

        if not action or action not in _HANDLERS:
            _json_response(self, {
                "error": "Missing or invalid 'action' parameter",
                "valid_actions": list(_HANDLERS.keys()),
            }, 400)
            return

        try:
            result = _HANDLERS[action](params)
            status = 200 if "error" not in result else 422
            _json_response(self, result, status, cache=_CACHE_HEADERS.get(action))
        except Exception:
            import traceback as _tb
            import secrets as _secrets
            trace_id = _secrets.token_hex(4)
            print(
                f"[api:{action}] trace_id={trace_id}\n{_tb.format_exc()}",
                file=sys.stderr,
            )
            _json_response(
                self,
                {"error": "Internal error", "trace_id": trace_id},
                500,
            )

    def do_OPTIONS(self):
        origin = _resolve_allowed_origin(self.headers.get("Origin", ""))
        self.send_response(204 if origin else 403)
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()
