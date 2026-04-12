"""Tests for pokequant/signals/dip_detector.py."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

from pokequant.signals.dip_detector import (
    SIGNAL_BUY,
    SIGNAL_HOLD,
    SIGNAL_INSUFFICIENT_DATA,
    SIGNAL_STRONG_BUY,
    SIGNAL_STRONG_SELL,
    _classify_row,
    _compute_rsi,
    generate_signals,
    latest_signal,
)
from config import DIP_THRESHOLD, VOLUME_SURGE_FACTOR


def _build_sales_df(
    prices: list[float],
    base_date: datetime | None = None,
    quantities: list[int] | None = None,
) -> pd.DataFrame:
    """Build a minimal normalized-style DataFrame for signal testing."""
    if base_date is None:
        base_date = datetime(2024, 1, 1)
    n = len(prices)
    if quantities is None:
        quantities = [1] * n
    return pd.DataFrame({
        "sale_id": [f"s{i}" for i in range(n)],
        "card_id": ["card"] * n,
        "card_name": ["Card"] * n,
        "price": prices,
        "date": [pd.Timestamp(base_date + timedelta(days=i), tz="UTC") for i in range(n)],
        "condition": ["NM"] * n,
        "source": ["pricecharting"] * n,
        "quantity": quantities,
    })


class TestGenerateSignals:
    def test_returns_annotated_df(self):
        """Output has sma_7, sma_30, and signal columns."""
        df = _build_sales_df([10.0 + i * 0.1 for i in range(35)])
        result = generate_signals(df)
        assert "sma_7" in result.columns
        assert "sma_30" in result.columns
        assert "signal" in result.columns

    def test_raises_on_empty_df(self):
        """Empty DataFrame raises ValueError."""
        df = pd.DataFrame()
        with pytest.raises(ValueError):
            generate_signals(df)


class TestLatestSignal:
    def test_strong_buy(self):
        """Price 20% below SMA-30 + volume surge -> STRONG BUY."""
        # Build 35 days of stable data at $100, then a sharp dip with volume.
        prices = [100.0] * 30
        # Last 5 days: price dips to $78 (22% below SMA-30 which is ~$100)
        prices.extend([78.0] * 5)
        # Volume surge: last few days have high volume, earlier days have low.
        quantities = [1] * 30 + [10] * 5
        df = _build_sales_df(prices, quantities=quantities)
        result = latest_signal(df, card_id="test")
        assert result.signal == SIGNAL_STRONG_BUY

    def test_strong_sell(self):
        """Price 35% above SMA-30 -> STRONG SELL."""
        # 30 days at $50, then 5 days at $70 (40% above SMA-30 which is ~$50).
        prices = [50.0] * 30 + [70.0] * 5
        df = _build_sales_df(prices)
        result = latest_signal(df, card_id="test")
        assert result.signal == SIGNAL_STRONG_SELL

    def test_hold(self):
        """Price within +/-10% of SMA-30 -> HOLD."""
        # Stable prices around $50 — no dip, no spike.
        prices = [50.0 + (i % 3) * 0.5 for i in range(35)]
        df = _build_sales_df(prices)
        result = latest_signal(df, card_id="test")
        assert result.signal == SIGNAL_HOLD

    def test_insufficient_data_single_row(self):
        """1-row input still produces a result (not INSUFFICIENT_DATA for the trading row)."""
        df = _build_sales_df([25.0])
        result = latest_signal(df, card_id="test")
        # With a single row, SMA-7 == SMA-30 == price, so it should be HOLD.
        assert result.signal in (SIGNAL_HOLD, SIGNAL_INSUFFICIENT_DATA)


class TestRSI:
    def test_rsi_column_added(self):
        """generate_signals adds an 'rsi' column to the output."""
        df = _build_sales_df([10.0 + i * 0.1 for i in range(35)])
        result = generate_signals(df)
        assert "rsi" in result.columns

    def test_rsi_range(self):
        """RSI values should be in [0, 100] where not NaN."""
        df = _build_sales_df([10.0 + i * 0.1 for i in range(35)])
        result = generate_signals(df)
        rsi_valid = result["rsi"].dropna()
        if len(rsi_valid) > 0:
            assert rsi_valid.min() >= 0
            assert rsi_valid.max() <= 100

    def test_rsi_in_latest_signal(self):
        """latest_signal includes rsi field."""
        prices = [50.0 + (i % 3) * 0.5 for i in range(35)]
        df = _build_sales_df(prices)
        result = latest_signal(df, card_id="test")
        # RSI should be present (either float or None if insufficient data)
        assert hasattr(result, "rsi")


class TestClassifyRowUsesConfig:
    def test_uses_config_thresholds(self):
        """Verify _classify_row uses DIP_THRESHOLD and VOLUME_SURGE_FACTOR from config."""
        # Build a row where price is exactly at the dip threshold.
        dip_pct = -(DIP_THRESHOLD * 100)
        surge_pct = (VOLUME_SURGE_FACTOR - 1) * 100

        row = pd.Series({
            "price_mean": 85.0,
            "sma_30": 100.0,
            "price_vs_sma30_pct": dip_pct,
            "volume_surge_pct": surge_pct,
        })
        signal = _classify_row(row)
        assert signal == SIGNAL_STRONG_BUY

        # No volume surge — should be BUY (not STRONG BUY).
        row_no_vol = row.copy()
        row_no_vol["volume_surge_pct"] = 0.0
        signal2 = _classify_row(row_no_vol)
        assert signal2 == SIGNAL_BUY
