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
        cost_basis = float(cost)
    except ValueError:
        return {"error": f"Invalid cost: '{cost}'"}

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
        "cmc": market_value,
        "cost_basis": cost_basis,
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
    import sys
    sys.path.insert(0, PROJECT_ROOT)
    from pokequant.analyze import _fetch_set_cards, _build_top3_tier_data
    from pokequant.ev.calculator import calculate_box_ev

    packs_per_box = int(params.get("packs", ["36"])[0])
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

    # Bucket by day, median price per day
    buckets: dict[str, list[float]] = defaultdict(list)
    for s in sales:
        try:
            d = str(s["date"])[:10]
            p = float(s["price"])
            if p > 0:
                buckets[d].append(p)
        except (KeyError, ValueError, TypeError):
            continue

    # Forward-fill missing days with previous value so the chart has no gaps
    if not buckets:
        return {"error": "No valid price data"}

    sorted_dates = sorted(buckets.keys())
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


_HANDLERS = {
    "price": _handle_price,
    "signal": _handle_signal,
    "flip": _handle_flip,
    "ev": _handle_ev,
    "bulk": _handle_bulk,
    "history": _handle_history,
    "grades": _handle_grades,
    "sales": _handle_sales,
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
