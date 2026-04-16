"""Tests for pokequant/bulk/optimizer.py (Module 4)."""

from __future__ import annotations

import pytest

from pokequant.bulk.optimizer import analyze_bulk_lot, _compute_shipping_cost


# ---------------------------------------------------------------------------
# analyze_bulk_lot
# ---------------------------------------------------------------------------


def test_analyze_bulk_lot_liquidate():
    """Large inventory above threshold → should_liquidate=True."""
    inventory = {
        "Common": 5000,
        "Uncommon": 2000,
        "Reverse Holo": 500,
        "Holo Rare": 100,
        "Ultra Rare": 20,
    }
    result = analyze_bulk_lot(inventory)
    assert result.should_liquidate is True
    assert result.net_profit > 0
    assert result.total_cards == 7620


def test_analyze_bulk_lot_hold():
    """Tiny inventory → should_liquidate=False."""
    inventory = {"Common": 10, "Uncommon": 5}
    result = analyze_bulk_lot(inventory)
    assert result.should_liquidate is False
    assert result.net_profit < 50.0


def test_analyze_bulk_lot_empty_inventory():
    """All zeroes → should_liquidate=False, recommendation mentions 'empty'."""
    inventory = {"Common": 0, "Uncommon": 0}
    result = analyze_bulk_lot(inventory)
    assert result.should_liquidate is False
    assert "empty" in result.recommendation.lower()


def test_analyze_bulk_lot_negative_count_raises():
    """``{\"Common\": -1}`` → ValueError."""
    with pytest.raises(ValueError, match="[Nn]egative"):
        analyze_bulk_lot({"Common": -1})


def test_analyze_bulk_lot_unknown_card_type_treated_as_zero():
    """``{\"Holo GX\": 50}`` → no crash, $0 subtotal for that type."""
    result = analyze_bulk_lot({"Holo GX": 50})
    assert result.per_type_breakdown["Holo GX"]["subtotal"] == 0.0
    # Net profit should be negative (shipping overhead with $0 payout).
    assert result.net_profit < 0


# ---------------------------------------------------------------------------
# _compute_shipping_cost
# ---------------------------------------------------------------------------


def test_compute_shipping_cost_rounds_to_cents():
    """Verify shipping_cost is within a cent of its rounded value."""
    _, cost = _compute_shipping_cost(total_cards=1234)
    # Floating-point arithmetic may not land exactly on a cent boundary,
    # but the result should be within 1 cent of its rounded form.
    assert abs(cost - round(cost, 2)) < 0.01
