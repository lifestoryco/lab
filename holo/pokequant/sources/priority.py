"""Adapter priority — tie-break when the reconciler sees duplicate records.

Higher wins. Thresholds:
  >= 70  — authoritative completed-sale sources
  30-69  — market estimates (never enter sale median)
  <= 29  — meta signals (no price, informational)
"""
from __future__ import annotations

ADAPTER_PRIORITY: dict[str, int] = {
    # Completed-sale records, authoritative
    "ebay_api": 100,
    "pricecharting": 90,
    "130point": 85,
    "ebay_html": 80,
    "goldin": 75,
    "cardmarket": 70,
    # Market estimates (never enter sale median)
    "tcgplayer_pro": 60,
    "tcgplayer_redirect": 50,
    "pricecharting_static": 40,
    "pokemontcg_synth": 30,
    # Meta signals
    "card_ladder": 20,
    "limitless": 10,
    "psa_pop": 5,
    "bgs_pop": 5,
}


def priority_for(adapter_name: str) -> int:
    return ADAPTER_PRIORITY.get(adapter_name, 0)
