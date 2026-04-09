"""
pokequant/ev/calculator.py
---------------------------
Module 3 — Sealed Product Expected Value (EV) Calculator

Responsibilities:
  1. Accept a JSON payload describing a booster box:
       - ``set_name``       : human-readable set name
       - ``packs_per_box``  : integer (e.g., 36)
       - ``retail_price``   : current sealed box price in USD
       - ``pull_rates``     : dict mapping tier names → pull rate + card list
  2. For each rarity tier, compute expected hits-per-box using the pull rate.
  3. Multiply expected hits by the per-card market value to get tier EV.
  4. Sum all tier EVs to get total box EV.
  5. Compare box EV to retail price and emit one of three recommendations.

Pull rate format accepted:
  "Secret Rare": {
      "rate": "1/36",      ← fraction string OR float (0.0278)
      "cards": [
          {"name": "Charizard ex SAR", "market_value": 85.00},
          {"name": "Pikachu ex SAR",   "market_value": 40.00}
      ]
  }

  The "rate" field represents packs-per-hit (inverse probability), e.g.:
  "1/36" means you statistically open one Secret Rare every 36 packs.

  Probability per pack = 1 / denominator (for "N/D" format) or raw float.
  Expected hits per box = probability_per_pack * packs_per_box.
  EV contribution = expected_hits * avg_card_value_in_tier.

Recommendation thresholds (from config.py):
  - EV > retail_price                         → "Positive EV: Rip for Singles"
  - EV within EV_BREAKEVEN_MARGIN of retail   → "Borderline: Context-Dependent"
  - EV < retail_price * (1 + EV_BREAKEVEN_MARGIN) → "Negative EV: Hold Sealed"
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import EV_BREAKEVEN_MARGIN, EV_POSITIVE_MARGIN

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Recommendation string constants
# ---------------------------------------------------------------------------
REC_RIP = "Positive EV: Rip for Singles"
REC_BORDERLINE = "Borderline: Context-Dependent"
REC_HOLD = "Negative EV: Hold Sealed"

# Pattern matching "N/D" fractional pull rates (e.g., "1/36", "3/72").
_FRACTION_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class TierEV:
    """Expected value breakdown for a single rarity tier."""
    tier_name: str
    pull_rate_per_pack: float       # Probability of hitting this tier in one pack
    expected_hits_per_box: float    # pull_rate_per_pack * packs_per_box
    avg_card_value: float           # Mean market value of cards in this tier
    tier_ev: float                  # expected_hits_per_box * avg_card_value
    card_count: int                 # Number of distinct cards in this tier


@dataclass
class BoxEVResult:
    """Full EV analysis result for a sealed booster box."""
    set_name: str
    packs_per_box: int
    retail_price: float
    total_ev: float
    ev_vs_retail: float             # total_ev - retail_price (positive = good)
    ev_vs_retail_pct: float         # (total_ev / retail_price - 1) * 100
    recommendation: str
    tier_breakdown: list[TierEV] = field(default_factory=list)

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            f"\n{'='*60}",
            f"  SET: {self.set_name}",
            f"  Packs/Box: {self.packs_per_box} | Retail: ${self.retail_price:.2f}",
            f"  Total EV:  ${self.total_ev:.2f}",
            f"  EV vs Retail: {self.ev_vs_retail:+.2f} "
            f"({self.ev_vs_retail_pct:+.1f}%)",
            f"  {'='*40}",
            f"  ► RECOMMENDATION: {self.recommendation}",
            f"  {'='*40}",
            "",
            "  Tier Breakdown:",
        ]
        for tier in self.tier_breakdown:
            lines.append(
                f"    {tier.tier_name:<22} "
                f"rate={tier.pull_rate_per_pack:.4f}  "
                f"hits={tier.expected_hits_per_box:.2f}  "
                f"avg=${tier.avg_card_value:.2f}  "
                f"EV=${tier.tier_ev:.2f}"
            )
        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_pull_rate(rate_value: Any) -> float:
    """Convert a pull rate value to a per-pack probability float.

    Accepted formats:
      - "1/36"  → 1/36 ≈ 0.02778
      - "3/72"  → 3/72 ≈ 0.04167
      - 0.0278  → used directly
      - "0.0278" → parsed to float

    Parameters
    ----------
    rate_value : str or float or int
        Raw value from the JSON ``rate`` field.

    Returns
    -------
    float
        Per-pack hit probability in the range (0, 1].

    Raises
    ------
    ValueError
        If the value cannot be interpreted as a valid probability.
    """
    if isinstance(rate_value, (int, float)):
        probability = float(rate_value)
    elif isinstance(rate_value, str):
        match = _FRACTION_RE.match(rate_value)
        if match:
            numerator = float(match.group(1))
            denominator = float(match.group(2))
            if denominator == 0:
                raise ValueError(
                    f"Pull rate denominator is zero in '{rate_value}'."
                )
            probability = numerator / denominator
        else:
            # Try plain float string.
            try:
                probability = float(rate_value)
            except ValueError:
                raise ValueError(
                    f"Cannot parse pull rate '{rate_value}'. "
                    "Expected 'N/D' fraction or a float."
                )
    else:
        raise TypeError(
            f"Pull rate must be a string or number, got {type(rate_value).__name__}."
        )

    if not (0 < probability <= 1):
        raise ValueError(
            f"Pull rate probability {probability:.6f} is outside (0, 1]. "
            "Check your rate value."
        )

    return probability


def _compute_tier_ev(
    tier_name: str,
    tier_data: dict[str, Any],
    packs_per_box: int,
) -> TierEV:
    """Compute EV contribution for one rarity tier.

    Parameters
    ----------
    tier_name : str
        Human-readable tier label (e.g., "Secret Rare").
    tier_data : dict
        Must contain 'rate' and 'cards' keys.
        Each card in 'cards' must have 'market_value'.
    packs_per_box : int
        Total packs in the box (used to compute expected hits).

    Returns
    -------
    TierEV

    Raises
    ------
    KeyError
        If 'rate' or 'cards' keys are missing.
    ValueError
        If any card is missing 'market_value', or if the value is
        non-numeric or negative.
    """
    # --- Validate required keys ---
    if "rate" not in tier_data:
        raise KeyError(
            f"Tier '{tier_name}' is missing the required 'rate' key."
        )
    if "cards" not in tier_data:
        raise KeyError(
            f"Tier '{tier_name}' is missing the required 'cards' key."
        )

    pull_prob: float = _parse_pull_rate(tier_data["rate"])

    cards: list[dict] = tier_data["cards"]
    if not cards:
        logger.warning(
            "Tier '%s' has an empty card list — contributing $0 EV.",
            tier_name,
        )
        return TierEV(
            tier_name=tier_name,
            pull_rate_per_pack=pull_prob,
            expected_hits_per_box=pull_prob * packs_per_box,
            avg_card_value=0.0,
            tier_ev=0.0,
            card_count=0,
        )

    # Collect market values with explicit error messages.
    values: list[float] = []
    for idx, card in enumerate(cards):
        card_name = card.get("name", f"Card #{idx}")
        if "market_value" not in card:
            raise KeyError(
                f"Card '{card_name}' in tier '{tier_name}' is missing "
                "'market_value'."
            )
        try:
            mv = float(card["market_value"])
        except (TypeError, ValueError):
            raise ValueError(
                f"Cannot convert market_value '{card['market_value']}' to "
                f"float for card '{card_name}' in tier '{tier_name}'."
            )
        if mv < 0:
            raise ValueError(
                f"market_value for card '{card_name}' in tier '{tier_name}' "
                f"is negative ({mv}). Prices must be ≥ 0."
            )
        values.append(mv)

    avg_value: float = sum(values) / len(values)
    expected_hits: float = pull_prob * packs_per_box
    tier_ev_val: float = expected_hits * avg_value

    logger.debug(
        "Tier '%s': prob=%.4f, hits=%.2f, avg_val=$%.2f, ev=$%.2f",
        tier_name,
        pull_prob,
        expected_hits,
        avg_value,
        tier_ev_val,
    )

    return TierEV(
        tier_name=tier_name,
        pull_rate_per_pack=pull_prob,
        expected_hits_per_box=expected_hits,
        avg_card_value=avg_value,
        tier_ev=tier_ev_val,
        card_count=len(cards),
    )


def _make_recommendation(
    total_ev: float,
    retail_price: float,
) -> str:
    """Select the recommendation string based on EV vs retail.

    Parameters
    ----------
    total_ev : float
        Computed expected value of a single box.
    retail_price : float
        Current market price of the sealed box.

    Returns
    -------
    str
        One of REC_RIP, REC_BORDERLINE, or REC_HOLD.
    """
    if retail_price <= 0:
        raise ValueError(f"retail_price must be positive, got {retail_price}.")

    ratio = total_ev / retail_price  # 1.0 means EV == retail

    # EV_POSITIVE_MARGIN = 0.00 means any EV ≥ retail is "Rip".
    # EV_BREAKEVEN_MARGIN = -0.05 means within 5% below retail is "Borderline".
    if ratio >= 1 + EV_POSITIVE_MARGIN:
        return REC_RIP
    elif ratio >= 1 + EV_BREAKEVEN_MARGIN:
        return REC_BORDERLINE
    else:
        return REC_HOLD


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_box_ev(box_data: dict[str, Any]) -> BoxEVResult:
    """Calculate the expected value of a sealed booster box.

    Parameters
    ----------
    box_data : dict
        Must contain:
          - ``set_name``      (str)
          - ``packs_per_box`` (int > 0)
          - ``retail_price``  (float > 0)
          - ``pull_rates``    (dict: tier_name → {rate, cards})

    Returns
    -------
    BoxEVResult
        Full EV analysis with tier breakdown and recommendation.

    Raises
    ------
    KeyError
        If any required top-level key is missing.
    ValueError
        If numeric fields are invalid, or if a tier's data is malformed.
    """
    # --- Validate top-level required keys ---
    for key in ("set_name", "packs_per_box", "retail_price", "pull_rates"):
        if key not in box_data:
            raise KeyError(
                f"Box data is missing required key '{key}'. "
                "Check your input JSON."
            )

    set_name: str = str(box_data["set_name"])

    try:
        packs_per_box = int(box_data["packs_per_box"])
    except (TypeError, ValueError):
        raise ValueError(
            f"Cannot convert packs_per_box '{box_data['packs_per_box']}' to int."
        )
    if packs_per_box <= 0:
        raise ValueError(f"packs_per_box must be > 0, got {packs_per_box}.")

    try:
        retail_price = float(box_data["retail_price"])
    except (TypeError, ValueError):
        raise ValueError(
            f"Cannot convert retail_price '{box_data['retail_price']}' to float."
        )
    if retail_price <= 0:
        raise ValueError(f"retail_price must be > 0, got {retail_price}.")

    pull_rates: dict = box_data["pull_rates"]
    if not isinstance(pull_rates, dict) or not pull_rates:
        raise ValueError(
            "pull_rates must be a non-empty dict mapping tier names to data."
        )

    # --- Compute EV for each tier ---
    tier_results: list[TierEV] = []
    total_ev: float = 0.0

    for tier_name, tier_data in pull_rates.items():
        tier = _compute_tier_ev(tier_name, tier_data, packs_per_box)
        tier_results.append(tier)
        total_ev += tier.tier_ev

    # Sort tiers by EV contribution descending for display clarity.
    tier_results.sort(key=lambda t: t.tier_ev, reverse=True)

    ev_vs_retail = total_ev - retail_price
    ev_vs_retail_pct = (total_ev / retail_price - 1) * 100
    recommendation = _make_recommendation(total_ev, retail_price)

    logger.info(
        "Box EV for '%s': total=$%.2f, retail=$%.2f, diff=%+.2f (%.1f%%) → %s",
        set_name,
        total_ev,
        retail_price,
        ev_vs_retail,
        ev_vs_retail_pct,
        recommendation,
    )

    return BoxEVResult(
        set_name=set_name,
        packs_per_box=packs_per_box,
        retail_price=retail_price,
        total_ev=total_ev,
        ev_vs_retail=ev_vs_retail,
        ev_vs_retail_pct=ev_vs_retail_pct,
        recommendation=recommendation,
        tier_breakdown=tier_results,
    )


def calculate_box_ev_from_file(filepath: str | Path) -> BoxEVResult:
    """Load a box EV JSON file from disk and calculate its EV.

    Parameters
    ----------
    filepath : str or Path
        Path to a JSON file containing a single box definition.

    Returns
    -------
    BoxEVResult
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Box EV input file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    return calculate_box_ev(data)


# ---------------------------------------------------------------------------
# Sample data for smoke-test
# ---------------------------------------------------------------------------
_SAMPLE_BOX = {
    "set_name": "Obsidian Flames",
    "packs_per_box": 36,
    "retail_price": 149.99,
    "pull_rates": {
        "Special Illustration Rare": {
            "rate": "1/36",
            "cards": [
                {"name": "Charizard ex SIR",       "market_value": 120.00},
                {"name": "Tyranitar ex SIR",        "market_value": 25.00},
                {"name": "Dragonite ex SIR",        "market_value": 18.00},
                {"name": "Pidgeot ex SIR",          "market_value": 15.00},
            ],
        },
        "Ultra Rare (ex)": {
            "rate": "1/6",
            "cards": [
                {"name": "Charizard ex",   "market_value": 30.00},
                {"name": "Tyranitar ex",   "market_value": 5.00},
                {"name": "Dragonite ex",   "market_value": 4.00},
                {"name": "Pidgeot ex",     "market_value": 3.50},
                {"name": "Revavroom ex",   "market_value": 2.00},
            ],
        },
        "Rare Holo": {
            "rate": "1/3",
            "cards": [
                {"name": "Arcanine",       "market_value": 1.50},
                {"name": "Magnezone",      "market_value": 1.25},
                {"name": "Vespiquen",      "market_value": 0.75},
            ],
        },
    },
}


if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s  %(name)s — %(message)s",
    )

    result = calculate_box_ev(_SAMPLE_BOX)
    print(result)
