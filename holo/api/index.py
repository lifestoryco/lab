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
from pathlib import Path
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Point cache to /tmp on Vercel (read-only filesystem outside /tmp).
os.environ.setdefault("HOLO_CACHE_DB", "/tmp/holo_cache.db")

# Add project root to path so pokequant imports work.
PROJECT_ROOT = str(Path(__file__).parents[1])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _json_response(handler, data: dict, status: int = 200):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Cache-Control", "s-maxage=300, stale-while-revalidate=600")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, default=str).encode())


_SOURCE_LABELS = {
    "tcgplayer": "TCGPlayer",
    "ebay": "eBay",
    "pricecharting": "PriceCharting",
    "pricecharting_static": "PriceCharting",
    "pokemontcg.io": "pokemontcg.io",
}


def _lookup_card_meta(card_name: str) -> dict:
    """Fetch card metadata (image, set, rarity, release date) from pokemontcg.io.

    Uses the name + optional number from the card query. Returns a dict with
    at minimum {image_small, image_large, set_name, rarity, number, release_date}
    or an empty dict if nothing found. Results are cached in /tmp via sqlite3.
    """
    import hashlib
    import re as _re
    import sqlite3
    import requests as _requests

    # Simple in-process cache keyed by slugified name.
    cache_db = os.environ.get("HOLO_CACHE_DB", "/tmp/holo_cache.db")
    slug = _re.sub(r"[^a-z0-9]+", "-", card_name.lower()).strip("-")
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
                (slug,),
            ).fetchone()
            if row:
                return json.loads(row[0])
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

    try:
        resp = _requests.get(
            "https://api.pokemontcg.io/v2/cards",
            params={"q": query, "pageSize": 25},
            headers={"User-Agent": "Mozilla/5.0 Holo/1.0"},
            timeout=8,
        )
        resp.raise_for_status()
        cards = resp.json().get("data", [])
    except Exception:
        return {}

    if not cards:
        # Fallback: try without exact-match quotes (pokemontcg.io fuzzy search)
        try:
            resp = _requests.get(
                "https://api.pokemontcg.io/v2/cards",
                params={"q": f"name:{query_name.split()[0]}*", "pageSize": 25},
                headers={"User-Agent": "Mozilla/5.0 Holo/1.0"},
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

    set_obj = best.get("set", {}) or {}
    images = best.get("images", {}) or {}
    meta = {
        "id": best.get("id", ""),
        "name": best.get("name", ""),
        "number": best.get("number", ""),
        "image_small": images.get("small", ""),
        "image_large": images.get("large", ""),
        "set_name": set_obj.get("name", ""),
        "set_series": set_obj.get("series", ""),
        "set_symbol": set_obj.get("images", {}).get("symbol", "") if isinstance(set_obj.get("images"), dict) else "",
        "set_logo": set_obj.get("images", {}).get("logo", "") if isinstance(set_obj.get("images"), dict) else "",
        "rarity": best.get("rarity", ""),
        "release_date": set_obj.get("releaseDate", ""),
        "tcgplayer_url": (best.get("tcgplayer") or {}).get("url", ""),
        # Extended TCG fields for Pokedex overlay.
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
        "set_printed_total": set_obj.get("printedTotal"),
        "set_total": set_obj.get("total"),
    }

    # Only cache non-empty results so transient API failures don't poison the cache.
    if meta.get("id"):
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


def _handle_pokedex(params: dict) -> dict:
    """Combined TCG metadata + PokeAPI species data for the Pokédex overlay."""
    card = params.get("card", [""])[0]
    if not card:
        return {"error": "Missing 'card' parameter"}
    meta = _lookup_card_meta(card)
    if not meta:
        return {"error": f"No card metadata found for '{card}'", "meta": {}, "species": {}}
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

    # Warn if all data came from the synthetic API fallback.
    synthetic_only = all(r.get("source") == "pokemontcg.io" for r in sales)

    comp = generate_comp_from_list(sales=sales, card_id="flip", card_name=card, n_sales=500)
    market_value = comp.cmc

    platform_fee = round(market_value * PLATFORM_FEE_RATE, 2)
    shipping_cost = SHIPPING_COST_BMWT if market_value >= SHIPPING_VALUE_THRESHOLD else SHIPPING_COST_PWE
    shipping_type = "BMWT" if market_value >= SHIPPING_VALUE_THRESHOLD else "PWE"
    net_revenue = round(market_value - platform_fee - shipping_cost, 2)
    profit = round(net_revenue - cost_basis, 2)
    margin_pct = round((profit / market_value) * 100, 1) if market_value > 0 else 0.0

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
    from datetime import date as _date, timedelta as _td
    from pokequant.scraper import fetch_sales

    try:
        limit = max(1, min(20, int(params.get("limit", ["8"])[0])))
    except ValueError:
        limit = 8
    try:
        window = max(3, min(30, int(params.get("window", ["7"])[0])))
    except ValueError:
        window = 7

    movers: list[dict] = []
    for name in _MOVERS_UNIVERSE:
        try:
            sales = fetch_sales(card_name=name, days=window, use_cache=True, grade="raw")
            if not isinstance(sales, list) or len(sales) < 2:
                continue

            # Outlier-filter the same way history does.
            raw_prices = [float(s["price"]) for s in sales
                          if float(s.get("price", 0)) > 0]
            if len(raw_prices) < 2:
                continue
            floor = statistics.median(raw_prices) * 0.15

            buckets: dict[str, list[float]] = defaultdict(list)
            for s in sales:
                try:
                    p = float(s["price"])
                    if p >= floor:
                        buckets[str(s["date"])[:10]].append(p)
                except (KeyError, ValueError, TypeError):
                    continue

            if len(buckets) < 2:
                continue

            sorted_dates = sorted(buckets.keys())
            first_price = statistics.median(buckets[sorted_dates[0]])
            last_price = statistics.median(buckets[sorted_dates[-1]])
            if first_price <= 0:
                continue

            change_pct = round((last_price / first_price - 1) * 100, 2)
            meta = _lookup_card_meta(name)

            movers.append({
                "card": name,
                "current": round(last_price, 2),
                "change_pct": change_pct,
                "direction": "up" if change_pct >= 0 else "down",
                "sales_count": len(sales),
                "image_small": meta.get("image_small", "") if meta else "",
                "name": meta.get("name", name) if meta else name,
                "number": meta.get("number", "") if meta else "",
            })
        except Exception:
            continue  # One card failing shouldn't tank the whole list.

    # Sort by absolute % change descending — biggest movers first.
    movers.sort(key=lambda m: abs(m["change_pct"]), reverse=True)
    return {
        "window_days": window,
        "count": min(len(movers), limit),
        "movers": movers[:limit],
    }


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
            _json_response(self, result, status)
        except Exception as exc:
            _json_response(self, {"error": str(exc)}, 500)
