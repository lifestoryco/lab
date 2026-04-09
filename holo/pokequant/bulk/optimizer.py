"""
pokequant/bulk/optimizer.py
----------------------------
Module 4 — Bulk ("Junk") Optimizer

Responsibilities:
  1. Accept an inventory dictionary mapping card types to card counts
     (e.g., {"Common": 500, "Uncommon": 300, "Reverse Holo": 120}).
  2. Apply current bulk payout rates (USD per card) to each tier.
  3. Model shipping costs based on total weight of the lot.
  4. Compute gross payout, estimated shipping cost, and net profit.
  5. Emit a ``should_liquidate`` boolean when net profit exceeds the
     BULK_LIQUIDATE_THRESHOLD defined in config.py.

Shipping model:
  - Weight per sleeved card ≈ 0.006 lbs (configurable in config.py).
  - Shipping rate is a flat USD-per-lb figure (USPS Media Mail estimate).
  - A fixed packaging overhead (box + bubble mailer) is added.

Design notes:
  - All card types not present in the payout_rates dict are treated as
    $0.00/card and logged as warnings rather than raising exceptions.
    This makes the function tolerant of custom or unusual card types.
  - The LiquidationResult dataclass carries a human-readable breakdown
    string for immediate CLI rendering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from config import (
    BULK_LIQUIDATE_THRESHOLD,
    BULK_WEIGHT_LBS_PER_CARD,
    DEFAULT_BULK_RATES,
    SHIPPING_RATE_PER_LB,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Packaging overhead in USD (envelope + box + tape + label).
# Keep separate from per-lb rate so it scales independently.
# ---------------------------------------------------------------------------
_PACKAGING_OVERHEAD_USD: float = 2.00


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


@dataclass
class LiquidationResult:
    """Full output of a bulk lot analysis.

    Attributes
    ----------
    total_cards : int
        Total card count across all types in the inventory.
    gross_payout : float
        Sum of (count * rate) across all card types before any deductions.
    estimated_weight_lbs : float
        Total lot weight including a packaging overhead assumption.
    shipping_cost : float
        Modelled shipping cost (weight * rate + packaging overhead).
    net_profit : float
        gross_payout - shipping_cost.
    should_liquidate : bool
        True when net_profit >= BULK_LIQUIDATE_THRESHOLD.
    liquidate_threshold : float
        The threshold used for the decision (from config or override).
    per_type_breakdown : dict[str, dict]
        Nested dict: {card_type: {count, rate, subtotal}}.
    recommendation : str
        Human-readable action string.
    """

    total_cards: int
    gross_payout: float
    estimated_weight_lbs: float
    shipping_cost: float
    net_profit: float
    should_liquidate: bool
    liquidate_threshold: float
    per_type_breakdown: dict[str, dict] = field(default_factory=dict)
    recommendation: str = ""

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            f"\n{'='*60}",
            f"  BULK OPTIMIZER — {'LIQUIDATE' if self.should_liquidate else 'HOLD'}",
            f"  {'='*58}",
            f"  Total cards:   {self.total_cards:,}",
            f"  Gross payout:  ${self.gross_payout:.2f}",
            f"  Weight:        {self.estimated_weight_lbs:.2f} lbs",
            f"  Shipping cost: ${self.shipping_cost:.2f}",
            f"  Net profit:    ${self.net_profit:.2f}",
            f"  Threshold:     ${self.liquidate_threshold:.2f}",
            f"",
            f"  Breakdown by type:",
        ]
        for card_type, info in self.per_type_breakdown.items():
            lines.append(
                f"    {card_type:<20} "
                f"count={info['count']:>6,}  "
                f"rate=${info['rate']:.4f}  "
                f"subtotal=${info['subtotal']:.2f}"
            )
        lines.append(f"\n  ► {self.recommendation}")
        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_inventory(inventory: dict[str, int]) -> None:
    """Raise descriptive errors for bad inventory input.

    Parameters
    ----------
    inventory : dict
        Maps card type strings to counts.

    Raises
    ------
    TypeError
        If ``inventory`` is not a dict.
    ValueError
        If any count is not a non-negative integer.
    """
    if not isinstance(inventory, dict):
        raise TypeError(
            f"inventory must be a dict, got {type(inventory).__name__}."
        )

    for card_type, count in inventory.items():
        if not isinstance(count, (int, float)):
            raise ValueError(
                f"Count for '{card_type}' must be numeric, "
                f"got {type(count).__name__}."
            )
        if count < 0:
            raise ValueError(
                f"Count for '{card_type}' is negative ({count}). "
                "Inventory cannot be negative."
            )


def _compute_shipping_cost(
    total_cards: int,
    weight_per_card_lbs: float = BULK_WEIGHT_LBS_PER_CARD,
    shipping_rate: float = SHIPPING_RATE_PER_LB,
    packaging_overhead: float = _PACKAGING_OVERHEAD_USD,
) -> tuple[float, float]:
    """Estimate total shipping cost and package weight.

    Parameters
    ----------
    total_cards : int
        Number of cards in the lot.
    weight_per_card_lbs : float
        Average weight per sleeved card in pounds.
    shipping_rate : float
        Carrier rate in USD per pound.
    packaging_overhead : float
        Fixed cost of packaging materials in USD.

    Returns
    -------
    tuple[float, float]
        (estimated_weight_lbs, total_shipping_cost_usd)
    """
    weight_lbs = total_cards * weight_per_card_lbs
    shipping_cost = (weight_lbs * shipping_rate) + packaging_overhead

    logger.debug(
        "Shipping model: %d cards × %.4f lb/card = %.2f lbs → "
        "$%.2f (rate $%.2f/lb + $%.2f overhead).",
        total_cards,
        weight_per_card_lbs,
        weight_lbs,
        shipping_cost,
        shipping_rate,
        packaging_overhead,
    )

    return weight_lbs, shipping_cost


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_bulk_lot(
    inventory: dict[str, int],
    payout_rates: dict[str, float] | None = None,
    liquidate_threshold: float = BULK_LIQUIDATE_THRESHOLD,
    weight_per_card_lbs: float = BULK_WEIGHT_LBS_PER_CARD,
    shipping_rate_per_lb: float = SHIPPING_RATE_PER_LB,
) -> LiquidationResult:
    """Analyze a bulk inventory lot and determine whether to liquidate.

    Parameters
    ----------
    inventory : dict[str, int]
        Maps card type labels to card counts.
        Example: {"Common": 500, "Reverse Holo": 80}
    payout_rates : dict[str, float] or None
        Maps card type labels to USD payout per card.
        Defaults to DEFAULT_BULK_RATES from config.py.
    liquidate_threshold : float
        Minimum net profit in USD to set should_liquidate=True.
    weight_per_card_lbs : float
        Override for weight model.
    shipping_rate_per_lb : float
        Override for carrier rate.

    Returns
    -------
    LiquidationResult
        Full analysis including per-type breakdown and recommendation.

    Raises
    ------
    TypeError
        If inventory is not a dict.
    ValueError
        If any inventory count is negative or non-numeric.
    """
    _validate_inventory(inventory)

    # Use default rates if none supplied.
    if payout_rates is None:
        payout_rates = DEFAULT_BULK_RATES

    per_type: dict[str, dict[str, Any]] = {}
    gross_payout: float = 0.0
    total_cards: int = 0

    for card_type, count in inventory.items():
        count_int = int(count)  # Normalize floats like 500.0 → 500

        # Gracefully handle unknown card types.
        rate = payout_rates.get(card_type)
        if rate is None:
            logger.warning(
                "Card type '%s' not found in payout_rates — treating as $0.00.",
                card_type,
            )
            rate = 0.0

        subtotal = count_int * rate
        gross_payout += subtotal
        total_cards += count_int

        per_type[card_type] = {
            "count": count_int,
            "rate": rate,
            "subtotal": subtotal,
        }

    if total_cards == 0:
        logger.warning("Inventory is empty — returning zero-profit result.")
        return LiquidationResult(
            total_cards=0,
            gross_payout=0.0,
            estimated_weight_lbs=0.0,
            shipping_cost=0.0,
            net_profit=0.0,
            should_liquidate=False,
            liquidate_threshold=liquidate_threshold,
            per_type_breakdown=per_type,
            recommendation="Inventory is empty. Nothing to liquidate.",
        )

    weight_lbs, shipping_cost = _compute_shipping_cost(
        total_cards,
        weight_per_card_lbs=weight_per_card_lbs,
        shipping_rate=shipping_rate_per_lb,
    )

    net_profit = gross_payout - shipping_cost
    should_liquidate = net_profit >= liquidate_threshold

    # Build recommendation string.
    if should_liquidate:
        recommendation = (
            f"Liquidate Bulk — net profit ${net_profit:.2f} exceeds "
            f"threshold ${liquidate_threshold:.2f}. "
            f"Ship {total_cards:,} cards ({weight_lbs:.1f} lbs)."
        )
    else:
        deficit = liquidate_threshold - net_profit
        recommendation = (
            f"Hold Bulk — net profit ${net_profit:.2f} is "
            f"${deficit:.2f} short of the ${liquidate_threshold:.2f} threshold. "
            f"Accumulate more cards before shipping."
        )

    logger.info(
        "Bulk analysis: %d cards, gross=$%.2f, shipping=$%.2f, "
        "net=$%.2f → %s",
        total_cards,
        gross_payout,
        shipping_cost,
        net_profit,
        "LIQUIDATE" if should_liquidate else "HOLD",
    )

    return LiquidationResult(
        total_cards=total_cards,
        gross_payout=gross_payout,
        estimated_weight_lbs=weight_lbs,
        shipping_cost=shipping_cost,
        net_profit=net_profit,
        should_liquidate=should_liquidate,
        liquidate_threshold=liquidate_threshold,
        per_type_breakdown=per_type,
        recommendation=recommendation,
    )


def add_cards_to_inventory(
    inventory: dict[str, int],
    additions: dict[str, int],
) -> dict[str, int]:
    """Merge a batch of new cards into an existing inventory dict.

    Both dicts are treated as immutable — a new merged dict is returned.

    Parameters
    ----------
    inventory : dict[str, int]
        Existing inventory.
    additions : dict[str, int]
        New cards to add.

    Returns
    -------
    dict[str, int]
        New inventory with counts summed.
    """
    merged = dict(inventory)  # Shallow copy — counts are ints (immutable).
    for card_type, count in additions.items():
        if count < 0:
            raise ValueError(
                f"Cannot add a negative count ({count}) for '{card_type}'."
            )
        merged[card_type] = merged.get(card_type, 0) + int(count)
    return merged


# ---------------------------------------------------------------------------
# Smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s  %(name)s — %(message)s",
    )

    sample_inventory = {
        "Common": 2_400,
        "Uncommon": 1_200,
        "Reverse Holo": 360,
        "Holo Rare": 80,
        "Ultra Rare": 5,
    }

    result = analyze_bulk_lot(sample_inventory)
    print(result)
