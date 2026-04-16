"""
pokequant/analyze.py
---------------------
Analysis Dispatcher — compact JSON output for Claude Code commands

Reads scraped sales data (or config arguments), runs the appropriate
pure-function module, and prints a compact JSON result to stdout.
Claude reads this JSON and renders the user-facing output.

All subcommands are designed for minimal token footprint:
  - stdout is always a single JSON object or array, nothing else
  - logging goes to stderr only (never pollutes stdout)
  - unhandled errors are caught and JSON-encoded so Claude can explain them

Usage:
  python pokequant/analyze.py signal --data '[{...}]'
  python pokequant/analyze.py ev --set "Obsidian Flames" --retail 149.99
  python pokequant/analyze.py bulk --commons 2400 --uncommons 1200
  python pokequant/analyze.py comp --data '[{...}]'
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

# Make the project root importable regardless of cwd.
sys.path.insert(0, str(Path(__file__).parents[1]))

from config import (
    FLIP_THIN_MARGIN_THRESHOLD_PCT,
    PLATFORM_FEE_RATE,
    SHIPPING_COST_BMWT,
    SHIPPING_COST_PWE,
    SHIPPING_VALUE_THRESHOLD,
)

import numpy as np
import pandas as pd
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# pokemontcg.io helpers (for EV subcommand)
# ---------------------------------------------------------------------------

_TCG_API = "https://api.pokemontcg.io/v2"

# Known pull rates per rarity string (probability per pack).
# Source: Bulbapedia / official set configuration docs.
# These are conservative estimates; adjust in config.py if needed.
_PULL_RATES: dict[str, str] = {
    "Special Illustration Rare": "1/36",
    "Hyper Rare": "1/36",
    "Secret Rare": "1/36",
    "Illustration Rare": "1/18",
    "Ultra Rare": "1/6",
    "Double Rare": "1/4",
    "Rare Holo ex": "1/6",
    "Rare Holo V": "1/6",
    "Rare Holo VMAX": "1/8",
    "Rare Holo VSTAR": "1/8",
    "Rare VMAX": "1/8",
    "Rare V": "1/6",
    "Rare Holo": "1/3",
    "Rare": "1/2",
}

# Packs per box for common modern sets.
_PACKS_PER_BOX_DEFAULT = 36

# User-Agent for API calls (same pool as scraper; pick one statically here).
_API_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)


def _fetch_set_cards(set_name: str) -> list[dict]:
    """Fetch all cards for a set from pokemontcg.io (no API key required).

    Returns a list of card dicts with 'name', 'rarity', and price data.
    """
    # Try to find set by name (fuzzy — API supports partial name search).
    url = f"{_TCG_API}/cards"
    params = {
        "q": f'set.name:"{set_name}"',
        "select": "id,name,rarity,tcgplayer,cardmarket",
        "pageSize": 250,
    }
    headers = {"User-Agent": _API_UA}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("data", [])
    except (requests.RequestException, json.JSONDecodeError) as exc:
        logger.error("pokemontcg.io API error: %s", exc)
        return []


def _extract_market_value(card: dict) -> float | None:
    """Extract the best available market price from a card dict."""
    tcg = card.get("tcgplayer", {}).get("prices", {})
    for variant in tcg.values():
        if isinstance(variant, dict):
            for key in ("market", "mid", "low"):
                val = variant.get(key)
                if val and isinstance(val, (int, float)) and val > 0:
                    return float(val)

    # Fallback: cardmarket average sell price.
    cm = card.get("cardmarket", {}).get("prices", {})
    val = cm.get("averageSellPrice") or cm.get("avg1")
    if val and isinstance(val, (int, float)) and val > 0:
        return float(val)

    return None


def _build_top3_tier_data(cards: list[dict], packs_per_box: int) -> dict:
    """Group cards by rarity, compute avg value, keep only top 3 tiers.

    The EV module only calculates the top 3 value-contributing tiers.
    Bulk commons/uncommons add noise and negligible EV — excluding them
    keeps compute and token costs lean.

    Returns a ``pull_rates`` dict ready for ``calculate_box_ev()``.
    """
    from collections import defaultdict

    tier_values: dict[str, list[float]] = defaultdict(list)

    for card in cards:
        rarity = card.get("rarity", "Unknown")
        val = _extract_market_value(card)
        if val and val > 0.25:  # Ignore bulk commons (< $0.25 market value)
            tier_values[rarity].append(val)

    # Log any rarities that have no pull rate — silently excluded from EV.
    unknown_rarities = [r for r in tier_values if r not in _PULL_RATES]
    if unknown_rarities:
        logger.warning(
            "Rarities with no pull rate data (excluded from EV): %s",
            unknown_rarities,
        )

    if not tier_values:
        return {}

    # Compute per-tier average and sort descending.
    tier_summary = [
        {"rarity": rarity, "avg_val": sum(vals) / len(vals), "cards": vals}
        for rarity, vals in tier_values.items()
        if rarity in _PULL_RATES  # Only tiers with known pull rates
    ]
    tier_summary.sort(key=lambda t: t["avg_val"], reverse=True)

    # Take top 3 tiers only.
    top3 = tier_summary[:3]

    pull_rates_dict: dict[str, dict] = {}
    for tier in top3:
        pull_rates_dict[tier["rarity"]] = {
            "rate": _PULL_RATES[tier["rarity"]],
            "cards": [{"name": tier["rarity"], "market_value": val}
                      for val in tier["cards"]],
        }

    return pull_rates_dict


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _out(data: Any) -> None:
    """Write compact JSON to stdout. This is the only stdout write."""
    print(json.dumps(data, separators=(",", ":"), default=str))


def _error_out(message: str, **extras) -> None:
    """Emit an error JSON and exit with code 1."""
    _out({"error": message, **extras})
    sys.exit(1)


def _extract_sources(records: list[dict]) -> list[dict]:
    """Summarise which data sources contributed to a sales dataset.

    Returns a list of {name, label, url, count} dicts, one per unique source,
    ordered by descending count.  Used to build hyperlinked source footers in
    Claude's rendered output.
    """
    _SOURCE_LABELS = {
        "tcgplayer":         "TCGPlayer",
        "ebay":              "eBay",
        "pricecharting":     "PriceCharting",
        "pricecharting_static": "PriceCharting",
        "pokemontcg.io":     "pokemontcg.io",
    }
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
        # Keep the first non-empty URL we encounter for this source.
        if not seen[src]["url"] and url:
            seen[src]["url"] = url
        seen[src]["count"] += 1
    return sorted(seen.values(), key=lambda s: s["count"], reverse=True)


# ---------------------------------------------------------------------------
# Subcommand: signal
# ---------------------------------------------------------------------------

def cmd_signal(args: argparse.Namespace) -> None:
    """Run SMA + volume signal analysis on scraped sales data."""
    # --- Parse input data ---
    try:
        raw = json.loads(args.data)
    except (json.JSONDecodeError, TypeError):
        _error_out("Invalid JSON in --data argument.")
        return

    # Handle error passthrough from scraper.
    if isinstance(raw, dict) and "error" in raw:
        _out({"error": "No liquid market found", "signal": "UNKNOWN",
              "detail": raw.get("error", "")})
        return

    if not isinstance(raw, list) or len(raw) == 0:
        _out({"error": "No liquid market found", "signal": "UNKNOWN"})
        return

    # Warn if all data comes from the synthetic API fallback (not real sold listings).
    if isinstance(raw, list) and raw and all(r.get("source") == "pokemontcg.io" for r in raw):
        _out({
            "error": "Only synthetic price data available (no real PriceCharting sales). "
                     "Signal analysis would be unreliable — try again when real sales exist.",
            "signal": "UNKNOWN",
        })
        return

    try:
        from pokequant.ingestion.normalizer import ingest_card
        from pokequant.signals.dip_detector import latest_signal

        # Build a minimal card record dict the normalizer expects.
        card_record = {
            "card_id": args.card_id or "holo_card",
            "name": args.card_name or "Card",
            "set": "Unknown",
            "sales": raw,
        }
        df = ingest_card(card_record)
        result = latest_signal(df, card_id=card_record["card_id"])

        _out({
            "signal": result.signal,
            "price": result.current_price,
            "sma7": result.sma_7,
            "sma30": result.sma_30,
            "dip_pct": result.price_vs_sma30_pct,
            "vol_3d": result.volume_3d,
            "vol_surge_pct": result.volume_surge_pct,
            "rsi": result.rsi,
            "sales_count": len(raw),
            "as_of": str(result.as_of_date.date()),
            "sources": _extract_sources(raw),
        })

    except Exception as exc:
        logger.error("Signal analysis failed: %s", exc, exc_info=True)
        _out({"error": f"Signal analysis failed: {exc}", "signal": "UNKNOWN"})


# ---------------------------------------------------------------------------
# Subcommand: ev
# ---------------------------------------------------------------------------

def cmd_ev(args: argparse.Namespace) -> None:
    """Calculate expected value for a sealed booster box."""
    try:
        from pokequant.ev.calculator import calculate_box_ev

        retail = args.retail
        set_name = args.set_name
        packs_per_box = args.packs or _PACKS_PER_BOX_DEFAULT

        # Slugify the set name for use as a cache key.
        import re as _re
        set_slug = "ev_" + _re.sub(r"[^a-z0-9]+", "-", set_name.lower().strip())

        # Try cache first — pokemontcg.io data for a set doesn't change hourly.
        from pokequant.scraper import cache_get, cache_put
        cached_cards = cache_get(set_slug, "tcgapi_set")
        if cached_cards is not None:
            logger.info("EV cache HIT for set '%s'.", set_name)
            cards = cached_cards
        else:
            cards = _fetch_set_cards(set_name)
            if cards:
                cache_put(set_slug, "tcgapi_set", cards)

        if not cards:
            _error_out(
                f"Could not find set '{set_name}' in the Pokémon TCG database. "
                "Check the set name spelling."
            )
            return

        pull_rates = _build_top3_tier_data(cards, packs_per_box)

        if not pull_rates:
            _error_out(
                f"Set '{set_name}' found but no known-rarity cards with pull rates. "
                "The set may be too new or the name may be slightly different."
            )
            return

        box_data = {
            "set_name": set_name,
            "packs_per_box": packs_per_box,
            "retail_price": retail,
            "pull_rates": pull_rates,
        }

        result = calculate_box_ev(box_data)

        # Find top card across all tiers.
        top_tier = result.tier_breakdown[0] if result.tier_breakdown else None
        top_card_name = top_tier.tier_name if top_tier else "Unknown"
        top_card_value = top_tier.avg_card_value if top_tier else 0.0

        _out({
            "set": result.set_name,
            "ev": round(result.total_ev, 2),
            "retail": result.retail_price,
            "delta": round(result.ev_vs_retail, 2),
            "delta_pct": round(result.ev_vs_retail_pct, 1),
            "rec": result.recommendation,
            "top_card": top_card_name,
            "top_card_value": round(top_card_value, 2),
            "tiers_analyzed": len(result.tier_breakdown),
            "cards_sampled": len(cards),
            "sources": [
                {
                    "label": "pokemontcg.io",
                    "url": f'https://api.pokemontcg.io/v2/cards?q=set.name:"{set_name}"',
                    "count": len(cards),
                    "note": "card data + TCGPlayer market prices",
                }
            ],
        })

    except Exception as exc:
        logger.error("EV analysis failed: %s", exc, exc_info=True)
        _out({"error": f"EV analysis failed: {exc}"})


# ---------------------------------------------------------------------------
# Subcommand: bulk
# ---------------------------------------------------------------------------

def cmd_bulk(args: argparse.Namespace) -> None:
    """Analyze bulk lot and emit liquidation recommendation."""
    try:
        from pokequant.bulk.optimizer import analyze_bulk_lot

        inventory: dict[str, int] = {}
        if args.commons:     inventory["Common"] = args.commons
        if args.uncommons:   inventory["Uncommon"] = args.uncommons
        if args.rev_holos:   inventory["Reverse Holo"] = args.rev_holos
        if args.holo_rares:  inventory["Holo Rare"] = args.holo_rares
        if args.ultra_rares: inventory["Ultra Rare"] = args.ultra_rares

        if not inventory:
            _out({"error": "No inventory provided. Pass --commons, --uncommons, etc."})
            return

        result = analyze_bulk_lot(inventory)

        _out({
            "net": round(result.net_profit, 2),
            "gross": round(result.gross_payout, 2),
            "shipping": round(result.shipping_cost, 2),
            "cards": result.total_cards,
            "weight_lbs": round(result.estimated_weight_lbs, 1),
            "liquidate": result.should_liquidate,
            "threshold": result.liquidate_threshold,
            "deficit": round(
                max(0.0, result.liquidate_threshold - result.net_profit), 2
            ),
            "breakdown": [
                {
                    "type": card_type,
                    "count": info["count"],
                    "rate": info["rate"],
                    "subtotal": round(info["subtotal"], 2),
                }
                for card_type, info in result.per_type_breakdown.items()
            ],
            "rates_source": "TCGPlayer / CFB bulk buylist averages (config.py)",
            "sources": [
                {
                    "label": "Holo bulk rates",
                    "note": (
                        "Buylist rates: Common $0.01 · Uncommon $0.02 · "
                        "Rev Holo $0.05 · Holo Rare $0.10 · Ultra Rare $0.50 · "
                        "Shipping: USPS Media Mail ~$0.50/lb + $2 packaging"
                    ),
                }
            ],
        })

    except Exception as exc:
        logger.error("Bulk analysis failed: %s", exc, exc_info=True)
        _out({"error": f"Bulk analysis failed: {exc}"})


# ---------------------------------------------------------------------------
# Subcommand: comp
# ---------------------------------------------------------------------------

def cmd_comp(args: argparse.Namespace) -> None:
    """Generate exponentially-weighted market comp with volatility score."""
    # --- Parse input data ---
    try:
        raw = json.loads(args.data)
    except (json.JSONDecodeError, TypeError):
        _error_out("Invalid JSON in --data argument.")
        return

    if isinstance(raw, dict) and "error" in raw:
        _out({"error": "No liquid market found", "cmc": None,
              "detail": raw.get("error", "")})
        return

    if not isinstance(raw, list) or len(raw) == 0:
        _out({"error": "No liquid market found", "cmc": None})
        return

    try:
        from pokequant.comps.generator import generate_comp_from_list

        result = generate_comp_from_list(
            sales=raw,
            card_id=args.card_id or "holo_card",
            card_name=args.card_name or "Card",
            n_sales=args.n_sales or 10,
            decay_lambda=args.decay or 0.3,
        )

        # Trend arrow: recent comp vs simple mean.
        if result.cmc_vs_mean_pct > 1.0:
            trend = f"↑ Rising {result.cmc_vs_mean_pct:+.1f}%"
        elif result.cmc_vs_mean_pct < -1.0:
            trend = f"↓ Softening {result.cmc_vs_mean_pct:+.1f}%"
        else:
            trend = "→ Stable"

        _out({
            "cmc": result.cmc,
            "mean": result.simple_mean,
            "delta_pct": result.cmc_vs_mean_pct,
            "trend": trend,
            "confidence": result.confidence,
            "volatility": result.volatility_score,
            "stddev": result.price_stddev,
            "sales_used": result.sales_used,
            "newest": str(result.newest_sale_date.date()),
            "oldest": str(result.oldest_sale_date.date()),
            "insufficient_data_warning": result.insufficient_data_warning,
            "sources": _extract_sources(raw),
        })

    except Exception as exc:
        logger.error("Comp analysis failed: %s", exc, exc_info=True)
        _out({"error": f"Comp analysis failed: {exc}", "cmc": None})


# ---------------------------------------------------------------------------
# Subcommand: flip
# ---------------------------------------------------------------------------

# All flip constants are imported from config.py — no module-level overrides.


def cmd_flip(args: argparse.Namespace) -> None:
    """Fetch live comp, apply platform fees + shipping, output personalized profit.

    Full pipeline in one call so the command file only needs to invoke
    analyze.py once — no separate scraper step for the user.
    """
    card_name: str = args.card
    cost_basis: float = args.cost
    method: str = args.method.lower()  # single | pack | box

    # Validate method.
    valid_methods = {"single", "pack", "box"}
    if method not in valid_methods:
        _out({"error": f"method must be one of: {', '.join(valid_methods)}. Got '{method}'."})
        return

    # --- Step 1: Fetch live sales (reuses scraper module directly) ---
    try:
        from pokequant.scraper import fetch_sales
        sales_result = fetch_sales(card_name=card_name, days=14, use_cache=True)
    except Exception as exc:
        _out({"error": f"Data fetch failed: {exc}", "card": card_name})
        return

    # Handle scraper error or empty result.
    if isinstance(sales_result, dict) and "error" in sales_result:
        logger.warning("Scraper returned error for '%s': %s", card_name, sales_result.get("error"))
        _out({
            "error": f"No market data found for '{card_name}'. "
                     "Check the spelling — use the exact card name as it appears on PriceCharting.",
            "card": card_name,
        })
        return

    if not isinstance(sales_result, list) or len(sales_result) == 0:
        _out({"error": "No liquid market found for this card.", "card": card_name})
        return

    # --- Step 2: Generate decay-weighted comp ---
    try:
        from pokequant.comps.generator import generate_comp_from_list
        comp = generate_comp_from_list(
            sales=sales_result,
            card_id="flip_card",
            card_name=card_name,
            n_sales=10,
            decay_lambda=0.3,
        )
        market_value: float = comp.cmc
    except Exception as exc:
        _out({"error": f"Comp generation failed: {exc}", "card": card_name})
        return

    # --- Step 3: Flip math ---
    platform_fee: float = round(market_value * PLATFORM_FEE_RATE, 2)

    # Shipping tier based on market value, not cost basis.
    if market_value >= SHIPPING_VALUE_THRESHOLD:
        shipping_cost = SHIPPING_COST_BMWT
        shipping_type = "BMWT"     # Bubble Mailer with Tracking
    else:
        shipping_cost = SHIPPING_COST_PWE
        shipping_type = "PWE"      # Plain White Envelope

    net_revenue: float = round(market_value - platform_fee - shipping_cost, 2)
    profit: float = round(net_revenue - cost_basis, 2)

    # Margin relative to the gross sale price (industry-standard for resellers).
    margin_pct: float = round((profit / market_value) * 100, 1) if market_value > 0 else 0.0

    # --- Step 4: Verdict ---
    if profit <= 0:
        verdict = "DO NOT SELL (Taking a loss)"
        verdict_emoji = "🔴"
    elif margin_pct < FLIP_THIN_MARGIN_THRESHOLD_PCT:
        verdict = "HOLD (Margins too thin)"
        verdict_emoji = "🟡"
    else:
        verdict = "FLIP IT"
        verdict_emoji = "🟢"

    # --- Step 5: Method-specific narrative note ---
    method_notes: dict[str, str] = {
        "single": "",  # Straight profit — no caveats needed.
        "pack": (
            "Based on pack cost. "
            "(Assumes other cards in the pack cover their own bulk value.)"
        ),
        "box": (
            "⚠️  Based on full box cost. "
            "You must sell the remaining hits in the box to realize this exact profit margin."
        ),
    }
    method_note = method_notes.get(method, "")

    # Acquisition label for display.
    method_labels = {"single": "Single", "pack": "Pack Pull", "box": "Box Pull"}

    _out({
        "card": card_name,
        "method": method,
        "method_label": method_labels.get(method, method.title()),
        "method_note": method_note,
        "cmc": market_value,
        "cost_basis": cost_basis,
        "platform_fee": platform_fee,
        "platform_fee_pct": PLATFORM_FEE_RATE * 100,
        "shipping_cost": shipping_cost,
        "shipping_type": shipping_type,
        "net_revenue": net_revenue,
        "profit": profit,
        "margin_pct": margin_pct,
        "verdict": verdict,
        "verdict_emoji": verdict_emoji,
        "comp_confidence": comp.confidence,
        "comp_sales_used": comp.sales_used,
        "insufficient_data_warning": comp.insufficient_data_warning,
    })


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="analyze",
        description="PokeQuant analysis dispatcher — outputs compact JSON to stdout",
    )
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug logging to stderr")
    subs = parser.add_subparsers(dest="subcommand", required=True)

    # signal
    p_sig = subs.add_parser("signal", help="SMA + volume signal")
    p_sig.add_argument("--data", required=True,
                       help="JSON array of sale records (from scraper.py stdout)")
    p_sig.add_argument("--card-id", dest="card_id", default="holo_card")
    p_sig.add_argument("--card-name", dest="card_name", default="Card")
    p_sig.set_defaults(func=cmd_signal)

    # ev
    p_ev = subs.add_parser("ev", help="Sealed box EV")
    p_ev.add_argument("--set", dest="set_name", required=True,
                      help='Set name, e.g. "Obsidian Flames"')
    p_ev.add_argument("--retail", type=float, required=True,
                      help="Sealed box retail price in USD")
    p_ev.add_argument("--packs", type=int, default=None,
                      help=f"Packs per box (default: {_PACKS_PER_BOX_DEFAULT})")
    p_ev.set_defaults(func=cmd_ev)

    # bulk
    p_bulk = subs.add_parser("bulk", help="Bulk liquidation optimizer")
    p_bulk.add_argument("--commons",     type=int, default=0)
    p_bulk.add_argument("--uncommons",   type=int, default=0)
    p_bulk.add_argument("--rev-holos",   type=int, default=0, dest="rev_holos")
    p_bulk.add_argument("--holo-rares",  type=int, default=0, dest="holo_rares")
    p_bulk.add_argument("--ultra-rares", type=int, default=0, dest="ultra_rares")
    p_bulk.set_defaults(func=cmd_bulk)

    # comp
    p_comp = subs.add_parser("comp", help="Exponential-decay weighted comp")
    p_comp.add_argument("--data", required=True,
                        help="JSON array of sale records (from scraper.py stdout)")
    p_comp.add_argument("--card-id", dest="card_id", default="holo_card")
    p_comp.add_argument("--card-name", dest="card_name", default="Card")
    p_comp.add_argument("--n-sales", dest="n_sales", type=int, default=10)
    p_comp.add_argument("--decay", type=float, default=0.3)
    p_comp.set_defaults(func=cmd_comp)

    # flip
    p_flip = subs.add_parser("flip", help="Personalized profit calculator")
    p_flip.add_argument("--card", required=True,
                        help='Card name, e.g. "Charizard V"')
    p_flip.add_argument("--cost", type=float, required=True,
                        help="Your cost basis in USD (what you paid for the card)")
    p_flip.add_argument("--method", choices=["single", "pack", "box"],
                        required=True,
                        help="How you acquired the card")
    p_flip.set_defaults(func=cmd_flip)

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = build_parser()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        print(json.dumps({"error": "No subcommand provided. Use: signal, ev, bulk, comp, or flip."}))
        sys.exit(1)
    args = parser.parse_args()

    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    args.func(args)
