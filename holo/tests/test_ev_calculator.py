"""Tests for pokequant/ev/calculator.py."""

from __future__ import annotations

import pytest

from pokequant.ev.calculator import (
    REC_HOLD,
    REC_RIP,
    _compute_tier_ev,
    _parse_pull_rate,
    calculate_box_ev,
)


class TestCalculateBoxEv:
    def test_positive_ev(self):
        """High-value box produces REC_RIP."""
        box_data = {
            "set_name": "Test Set",
            "packs_per_box": 36,
            "retail_price": 50.00,
            "pull_rates": {
                "Chase Tier": {
                    "rate": "1/6",
                    "cards": [
                        {"name": "Big Card", "market_value": 100.00},
                    ],
                },
            },
        }
        result = calculate_box_ev(box_data)
        assert result.total_ev > result.retail_price
        assert result.recommendation == REC_RIP

    def test_negative_ev(self):
        """Low-value box produces REC_HOLD."""
        box_data = {
            "set_name": "Bad Set",
            "packs_per_box": 36,
            "retail_price": 149.99,
            "pull_rates": {
                "Junk Tier": {
                    "rate": "1/36",
                    "cards": [
                        {"name": "Cheap Card", "market_value": 2.00},
                    ],
                },
            },
        }
        result = calculate_box_ev(box_data)
        assert result.total_ev < result.retail_price
        assert result.recommendation == REC_HOLD

    def test_missing_key_raises(self):
        """Missing 'packs_per_box' raises KeyError."""
        box_data = {
            "set_name": "Test",
            "retail_price": 100.0,
            "pull_rates": {},
        }
        with pytest.raises(KeyError, match="packs_per_box"):
            calculate_box_ev(box_data)

    def test_zero_packs_raises(self):
        """packs_per_box=0 raises ValueError."""
        box_data = {
            "set_name": "Test",
            "packs_per_box": 0,
            "retail_price": 100.0,
            "pull_rates": {"Tier": {"rate": "1/6", "cards": []}},
        }
        with pytest.raises(ValueError, match="packs_per_box"):
            calculate_box_ev(box_data)


class TestParsePullRate:
    def test_fraction(self):
        """'1/36' parses to ~0.02778."""
        result = _parse_pull_rate("1/36")
        assert abs(result - 1 / 36) < 0.0001

    def test_float_string(self):
        """'0.05' parses to 0.05."""
        result = _parse_pull_rate("0.05")
        assert result == 0.05

    def test_invalid_raises(self):
        """'not/a/rate' raises ValueError."""
        with pytest.raises(ValueError):
            _parse_pull_rate("not/a/rate")


class TestComputeTierEv:
    def test_empty_cards_returns_zero(self):
        """Tier with empty card list produces tier_ev == 0.0."""
        tier_data = {"rate": "1/6", "cards": []}
        result = _compute_tier_ev("Empty Tier", tier_data, packs_per_box=36)
        assert result.tier_ev == 0.0
        assert result.card_count == 0
