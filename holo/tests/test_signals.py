"""Tests for pokequant/signals/dip_detector.py (Module 2)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from pokequant.signals.dip_detector import (
    SIGNAL_BUY,
    SIGNAL_HOLD,
    SIGNAL_INSUFFICIENT_DATA,
    SIGNAL_SELL,
    SIGNAL_STRONG_BUY,
    SIGNAL_STRONG_SELL,
    _classify_row,
    generate_signals,
    latest_signal,
)
from config import DIP_THRESHOLD, RSI_OVERBOUGHT, RSI_OVERSOLD, SMA_LONG_WINDOW, VOLUME_SURGE_FACTOR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_sales_df(
    n_days: int = 35,
    base_price: float = 10.0,
    price_fn=None,
    volume: int = 1,
) -> pd.DataFrame:
    """Build a minimal sales DataFrame suitable for the signal pipeline.

    Parameters
    ----------
    price_fn : callable or None
        Takes (day_index, base_price) and returns a float price.
        If None, uses a flat base_price.
    """
    today = datetime.utcnow().date()
    rows = []
    for i in range(n_days):
        price = price_fn(i, base_price) if price_fn else base_price
        rows.append({
            "sale_id": f"sig_{i:03d}",
            "card_id": "sig_card",
            "card_name": "Signal Card",
            "set_name": "Set",
            "language": "EN",
            "price": price,
            "date": pd.Timestamp(today - timedelta(days=n_days - 1 - i), tz="UTC"),
            "condition": "NM",
            "source": "pricecharting",
            "quantity": volume,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# generate_signals
# ---------------------------------------------------------------------------


def test_generate_signals_returns_annotated_df():
    """Output must have sma_7, sma_30, and signal columns."""
    df = _build_sales_df()
    daily = generate_signals(df)
    assert "sma_7" in daily.columns
    assert "sma_30" in daily.columns
    assert "signal" in daily.columns


def test_generate_signals_raises_on_empty_df():
    """Empty DataFrame → ValueError."""
    with pytest.raises(ValueError, match="[Ee]mpty"):
        generate_signals(pd.DataFrame())


# ---------------------------------------------------------------------------
# latest_signal — composite signals
# ---------------------------------------------------------------------------


def test_latest_signal_strong_buy():
    """Price 20% below SMA-30 + volume surge → STRONG BUY."""
    def price_fn(i, base):
        # First 30 days at base, last 5 days drop 25%.
        if i >= 30:
            return base * 0.75
        return base

    df = _build_sales_df(n_days=35, base_price=100.0, price_fn=price_fn, volume=5)
    result = latest_signal(df, card_id="test")
    assert result.signal == SIGNAL_STRONG_BUY


def test_latest_signal_strong_sell():
    """Price 35% above SMA-30 → STRONG SELL."""
    def price_fn(i, base):
        if i >= 30:
            return base * 1.45
        return base

    df = _build_sales_df(n_days=35, base_price=100.0, price_fn=price_fn, volume=1)
    result = latest_signal(df, card_id="test")
    assert result.signal == SIGNAL_STRONG_SELL


def test_latest_signal_hold():
    """Price within ±10% of SMA-30 → HOLD."""
    df = _build_sales_df(n_days=35, base_price=100.0, volume=1)
    result = latest_signal(df, card_id="test")
    assert result.signal == SIGNAL_HOLD


def test_latest_signal_insufficient_data():
    """1-row input produces a result (may be HOLD due to partial SMA)."""
    today = datetime.utcnow().date()
    df = pd.DataFrame([{
        "sale_id": "one",
        "card_id": "single",
        "card_name": "Single",
        "set_name": "S",
        "language": "EN",
        "price": 10.0,
        "date": pd.Timestamp(today, tz="UTC"),
        "condition": "NM",
        "source": "pricecharting",
        "quantity": 1,
    }])
    result = latest_signal(df, card_id="single")
    # With 1 data point, SMA-7 == SMA-30 == price, so HOLD is expected.
    assert result.signal in (SIGNAL_HOLD, SIGNAL_INSUFFICIENT_DATA)


# ---------------------------------------------------------------------------
# _classify_row uses config thresholds
# ---------------------------------------------------------------------------


def test_classify_row_uses_config_thresholds():
    """Verify that DIP_THRESHOLD and VOLUME_SURGE_FACTOR from config.py are used."""
    sma_long_col = f"sma_{SMA_LONG_WINDOW}"
    # Price exactly at the DIP_THRESHOLD below SMA-30, no volume surge.
    row = pd.Series({
        "price_mean": 100.0 * (1 - DIP_THRESHOLD),
        sma_long_col: 100.0,
        "price_vs_sma30_pct": -DIP_THRESHOLD * 100,
        "volume_surge_pct": 0.0,  # No surge
    })
    signal = _classify_row(row)
    assert signal == SIGNAL_BUY

    # Now add volume surge at exactly the threshold.
    row["volume_surge_pct"] = (VOLUME_SURGE_FACTOR - 1) * 100
    signal = _classify_row(row)
    assert signal == SIGNAL_STRONG_BUY


# ---------------------------------------------------------------------------
# RSI (Step 9 enhancement)
# ---------------------------------------------------------------------------


def test_generate_signals_has_rsi_column():
    """Output must include an rsi column."""
    df = _build_sales_df()
    daily = generate_signals(df)
    assert "rsi" in daily.columns


def test_rsi_oversold_triggers_strong_buy():
    """RSI below oversold threshold + price dip → STRONG BUY (even without volume surge)."""
    sma_long_col = f"sma_{SMA_LONG_WINDOW}"
    row = pd.Series({
        "price_mean": 100.0 * (1 - DIP_THRESHOLD),
        sma_long_col: 100.0,
        "price_vs_sma30_pct": -DIP_THRESHOLD * 100,
        "volume_surge_pct": 0.0,  # No volume surge
        "rsi": RSI_OVERSOLD - 5,  # Oversold
    })
    signal = _classify_row(row)
    assert signal == SIGNAL_STRONG_BUY


def test_rsi_overbought_escalates_sell_to_strong_sell():
    """RSI above overbought + elevated price → STRONG SELL."""
    sma_long_col = f"sma_{SMA_LONG_WINDOW}"
    # Price is elevated (15% above) but not very elevated (30%).
    # Without RSI, this would be just SELL. With RSI overbought, it becomes STRONG SELL.
    row = pd.Series({
        "price_mean": 120.0,
        sma_long_col: 100.0,
        "price_vs_sma30_pct": 20.0,
        "volume_surge_pct": 0.0,
        "rsi": RSI_OVERBOUGHT + 5,  # Overbought
    })
    signal = _classify_row(row)
    assert signal == SIGNAL_STRONG_SELL


def test_latest_signal_includes_rsi():
    """latest_signal result should include an rsi field."""
    df = _build_sales_df(n_days=35, base_price=100.0, volume=1)
    result = latest_signal(df, card_id="test")
    # RSI may be None with limited data, but the field must exist.
    assert hasattr(result, "rsi")
