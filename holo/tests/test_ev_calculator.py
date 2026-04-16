"""Tests for pokequant/ev/calculator.py (Module 3)."""

from __future__ import annotations

import pytest

from pokequant.ev.calculator import (
    REC_HOLD,
    REC_RIP,
    _compute_tier_ev,
    _parse_pull_rate,
    calculate_box_ev,
)


# ---------------------------------------------------------------------------
# calculate_box_ev
# ---------------------------------------------------------------------------


def test_calculate_box_ev_positive_ev(sample_box_data):
    """Manually crafted high-value box → REC_RIP."""
    # Inflate card values so EV > retail.
    for tier in sample_box_data["pull_rates"].values():
        for card in tier["cards"]:
            card["market_value"] *= 5
    result = calculate_box_ev(sample_box_data)
    assert result.recommendation == REC_RIP
    assert result.total_ev > result.retail_price


def test_calculate_box_ev_negative_ev(sample_box_data):
    """Low-value box → REC_HOLD."""
    # Deflate card values so EV << retail.
    for tier in sample_box_data["pull_rates"].values():
        for card in tier["cards"]:
            card["market_value"] = 0.10
    result = calculate_box_ev(sample_box_data)
    assert result.recommendation == REC_HOLD
    assert result.total_ev < result.retail_price


def test_calculate_box_ev_missing_key_raises():
    """Missing ``packs_per_box`` → KeyError."""
    data = {"set_name": "X", "retail_price": 100, "pull_rates": {}}
    with pytest.raises(KeyError, match="packs_per_box"):
        calculate_box_ev(data)


def test_calculate_box_ev_zero_packs_raises():
    """``packs_per_box=0`` → ValueError."""
    data = {
        "set_name": "X",
        "packs_per_box": 0,
        "retail_price": 100,
        "pull_rates": {"Rare": {"rate": "1/3", "cards": [{"name": "A", "market_value": 1}]}},
    }
    with pytest.raises(ValueError, match="packs_per_box"):
        calculate_box_ev(data)


# ---------------------------------------------------------------------------
# _parse_pull_rate
# ---------------------------------------------------------------------------


def test_parse_pull_rate_fraction():
    """``\"1/36\"`` → 0.02778 (±0.0001)."""
    result = _parse_pull_rate("1/36")
    assert abs(result - 1 / 36) < 0.0001


def test_parse_pull_rate_float_string():
    """``\"0.05\"`` → 0.05."""
    assert _parse_pull_rate("0.05") == pytest.approx(0.05)


def test_parse_pull_rate_invalid_raises():
    """``\"not/a/rate\"`` → ValueError."""
    with pytest.raises(ValueError):
        _parse_pull_rate("not/a/rate")


# ---------------------------------------------------------------------------
# _compute_tier_ev
# ---------------------------------------------------------------------------


def test_compute_tier_ev_empty_cards_returns_zero():
    """Tier with empty card list → tier_ev == 0.0."""
    tier_data = {"rate": "1/6", "cards": []}
    result = _compute_tier_ev("Empty Tier", tier_data, packs_per_box=36)
    assert result.tier_ev == 0.0
    assert result.card_count == 0
