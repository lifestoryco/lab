"""Tests for pokequant/bulk/optimizer.py."""

from __future__ import annotations

import pytest

from pokequant.bulk.optimizer import analyze_bulk_lot, _compute_shipping_cost


class TestAnalyzeBulkLot:
    def test_liquidate(self):
        """Large inventory above threshold -> should_liquidate=True."""
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

    def test_hold(self):
        """Tiny inventory -> should_liquidate=False."""
        inventory = {"Common": 10, "Uncommon": 5}
        result = analyze_bulk_lot(inventory)
        assert result.should_liquidate is False

    def test_empty_inventory(self):
        """All zeroes -> should_liquidate=False, recommendation mentions 'empty'."""
        inventory = {"Common": 0, "Uncommon": 0}
        result = analyze_bulk_lot(inventory)
        assert result.should_liquidate is False
        assert "empty" in result.recommendation.lower()

    def test_negative_count_raises(self):
        """{'Common': -1} raises ValueError."""
        with pytest.raises(ValueError, match="negative"):
            analyze_bulk_lot({"Common": -1})

    def test_unknown_card_type_treated_as_zero(self):
        """Unknown card type ('Holo GX') -> no crash, $0 subtotal."""
        inventory = {"Holo GX": 50}
        result = analyze_bulk_lot(inventory)
        assert result.per_type_breakdown["Holo GX"]["subtotal"] == 0.0
        assert result.total_cards == 50


class TestComputeShippingCost:
    def test_rounds_to_cents(self):
        """Shipping cost should be representable as dollars and cents."""
        _, cost = _compute_shipping_cost(
            total_cards=100,
            weight_per_card_lbs=0.013,
            shipping_rate=0.50,
            packaging_overhead=2.00,
        )
        # Check it's a valid float that rounds to 2 decimal places cleanly.
        assert round(cost, 2) == cost or abs(round(cost, 2) - cost) < 1e-10
