"""
pokequant/signals/dip_detector.py
-----------------------------------
Module 2 — Market Arbitrage & Dip Detection (The "Buy/Sell" Engine)

Responsibilities:
  1. Aggregate per-day price (mean) and volume (sum of quantity) from the
     clean, normalized sales DataFrame produced by Module 1.
  2. Compute a 7-day Simple Moving Average (SMA-7) and a 30-day Simple
     Moving Average (SMA-30) on the daily mean price series.
  3. Evaluate the three-condition composite signal:
       a. Current price is ≥ DIP_THRESHOLD (15%) below SMA-30 → dip confirmed
       b. 3-day rolling volume is ≥ VOLUME_SURGE_FACTOR (20%) above its own
          rolling mean → liquidity surge confirmed
       c. Combined → "STRONG BUY (Rebound Expected)"
  4. Also emit SELL when price is significantly above SMA-30, and HOLD
     for everything in between.

Signal taxonomy (string constants exported at module level):
  SIGNAL_STRONG_BUY  = "STRONG BUY (Rebound Expected)"
  SIGNAL_BUY         = "BUY"
  SIGNAL_HOLD        = "HOLD"
  SIGNAL_SELL        = "SELL"
  SIGNAL_STRONG_SELL = "STRONG SELL"
  SIGNAL_INSUFFICIENT_DATA = "INSUFFICIENT DATA"

Design notes:
  - All rolling windows use min_periods=1 so early rows still get a value.
  - Volume baseline is computed as the rolling mean of daily volume over the
    SMA_LONG_WINDOW. This gives context-aware liquidity comparison.
  - The `generate_signals` function returns a fully annotated DataFrame —
    callers can inspect every intermediate column for debugging.
  - `latest_signal` is a convenience wrapper returning just the last row's
    signal, price, and SMA values as a plain dict.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from config import (
    DIP_THRESHOLD,
    SMA_LONG_WINDOW,
    SMA_SHORT_WINDOW,
    STRONG_SELL_THRESHOLD,
    VOLUME_LOOKBACK_DAYS,
    VOLUME_SURGE_FACTOR,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal constants — use these strings everywhere (no magic literals).
# ---------------------------------------------------------------------------
SIGNAL_STRONG_BUY = "STRONG BUY (Rebound Expected)"
SIGNAL_BUY = "BUY"
SIGNAL_HOLD = "HOLD"
SIGNAL_SELL = "SELL"
SIGNAL_STRONG_SELL = "STRONG SELL"
SIGNAL_INSUFFICIENT_DATA = "INSUFFICIENT DATA"

# Threshold above SMA-30 for a SELL signal (mirror of DIP_THRESHOLD).
_SELL_THRESHOLD = DIP_THRESHOLD       # 15% above SMA-30 → SELL
# STRONG_SELL_THRESHOLD imported from config.py


# ---------------------------------------------------------------------------
# Data container for a single signal evaluation result.
# ---------------------------------------------------------------------------
@dataclass
class SignalResult:
    """Structured output from `latest_signal`.

    Attributes
    ----------
    card_id : str
        Identifier of the evaluated card.
    signal : str
        One of the SIGNAL_* constants defined at module level.
    current_price : float
        The mean sale price on the most recent date with data.
    sma_7 : float | None
        7-day SMA on the most recent date (None if insufficient data).
    sma_30 : float | None
        30-day SMA on the most recent date (None if insufficient data).
    price_vs_sma30_pct : float | None
        Percentage deviation of current price from SMA-30.
        Negative means price is below SMA-30 (potential dip).
    volume_3d : float
        Total quantity sold over the last 3 available trading days.
    volume_baseline : float | None
        Rolling mean daily volume (long-window baseline).
    volume_surge_pct : float | None
        Percentage by which 3-day volume exceeds the baseline.
    as_of_date : pd.Timestamp
        The date of the most recent data point used for this signal.
    metadata : dict
        Any extra key/value pairs attached during evaluation.
    """

    card_id: str
    signal: str
    current_price: float
    sma_7: float | None
    sma_30: float | None
    price_vs_sma30_pct: float | None
    volume_3d: float
    volume_baseline: float | None
    volume_surge_pct: float | None
    rsi: float | None
    as_of_date: pd.Timestamp
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"[{self.as_of_date.date()}] {self.card_id} → {self.signal}\n"
            f"  Price: ${self.current_price:.2f} | "
            f"SMA-7: {f'${self.sma_7:.2f}' if self.sma_7 else 'N/A'} | "
            f"SMA-30: {f'${self.sma_30:.2f}' if self.sma_30 else 'N/A'}\n"
            f"  Price vs SMA-30: "
            f"{f'{self.price_vs_sma30_pct:+.1f}%' if self.price_vs_sma30_pct is not None else 'N/A'} | "
            f"3d Vol: {self.volume_3d:.0f} | "
            f"Vol Surge: "
            f"{f'{self.volume_surge_pct:+.1f}%' if self.volume_surge_pct is not None else 'N/A'}"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _aggregate_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse the sales DataFrame to one row per calendar date.

    Aggregations:
      - ``price_mean``  : mean sale price across all transactions that day.
      - ``price_low``   : minimum price (useful for range analysis).
      - ``price_high``  : maximum price.
      - ``volume``      : sum of ``quantity`` (total units sold).
      - ``num_transactions`` : raw count of sale records.

    The index is set to the ``date`` column and filled for any missing
    calendar days using NaN (forward-fill is intentionally NOT applied here
    — rolling windows handle sparse data better with NaN than stale prices).

    Parameters
    ----------
    df : pd.DataFrame
        Normalized sales DataFrame from `normalizer.ingest_card`.

    Returns
    -------
    pd.DataFrame
        Date-indexed daily aggregation sorted ascending.
    """
    if "date" not in df.columns or "price" not in df.columns:
        raise ValueError(
            "Input DataFrame must contain 'date' and 'price' columns."
        )

    daily = (
        df.groupby(df["date"].dt.normalize())  # normalize to midnight UTC
        .agg(
            price_mean=("price", "mean"),
            price_low=("price", "min"),
            price_high=("price", "max"),
            volume=("quantity", "sum"),
            num_transactions=("sale_id", "count"),
        )
        .sort_index()
    )

    # Reindex to a complete date range so rolling windows account for
    # calendar gaps (weekends, no-sale days).
    full_range = pd.date_range(
        start=daily.index.min(), end=daily.index.max(), freq="D", tz="UTC"
    )
    daily = daily.reindex(full_range)
    daily.index.name = "date"

    logger.debug(
        "Aggregated to %d calendar day(s) (%d trading day(s) with sales).",
        len(daily),
        daily["price_mean"].notna().sum(),
    )
    return daily


def _compute_smas(daily: pd.DataFrame) -> pd.DataFrame:
    """Append SMA columns to the daily aggregated DataFrame.

    Uses a centered=False rolling window (trailing) with min_periods=1
    so that early rows receive a partial-window average instead of NaN.

    Adds columns:
      - ``sma_{SMA_SHORT_WINDOW}``  (e.g., sma_7)
      - ``sma_{SMA_LONG_WINDOW}``   (e.g., sma_30)
      - ``price_vs_sma30_pct``      percentage deviation from sma_30

    Parameters
    ----------
    daily : pd.DataFrame
        Date-indexed DataFrame with a ``price_mean`` column.

    Returns
    -------
    pd.DataFrame
        The same DataFrame with SMA and deviation columns appended.
    """
    sma_short_col = f"sma_{SMA_SHORT_WINDOW}"
    sma_long_col = f"sma_{SMA_LONG_WINDOW}"

    daily[sma_short_col] = (
        daily["price_mean"]
        .rolling(window=SMA_SHORT_WINDOW, min_periods=1)
        .mean()
    )

    daily[sma_long_col] = (
        daily["price_mean"]
        .rolling(window=SMA_LONG_WINDOW, min_periods=1)
        .mean()
    )

    # Percentage deviation of current price from the long-term SMA.
    # Negative value → price is below SMA-30 → potential dip.
    daily["price_vs_sma30_pct"] = (
        (daily["price_mean"] - daily[sma_long_col]) / daily[sma_long_col] * 100
    )

    logger.debug(
        "Computed SMA-%d and SMA-%d columns.",
        SMA_SHORT_WINDOW,
        SMA_LONG_WINDOW,
    )
    return daily


def _compute_volume_signals(daily: pd.DataFrame) -> pd.DataFrame:
    """Append volume liquidity columns to the daily DataFrame.

    Adds columns:
      - ``volume_3d``      : rolling sum of volume over VOLUME_LOOKBACK_DAYS.
      - ``volume_baseline``: rolling mean of daily volume over SMA_LONG_WINDOW
                             (gives context-aware normal volume).
      - ``volume_surge_pct``: how much ``volume_3d`` exceeds ``volume_baseline``
                               as a percentage.

    Parameters
    ----------
    daily : pd.DataFrame
        Date-indexed DataFrame with a ``volume`` column.

    Returns
    -------
    pd.DataFrame
        The same DataFrame with volume signal columns appended.
    """
    # 3-day rolling volume sum — filled with 0 where no sales occurred.
    volume_filled = daily["volume"].fillna(0)

    daily["volume_3d"] = (
        volume_filled
        .rolling(window=VOLUME_LOOKBACK_DAYS, min_periods=1)
        .sum()
    )

    # Long-window rolling mean volume as the baseline for "normal" activity.
    daily["volume_baseline"] = (
        volume_filled
        .rolling(window=SMA_LONG_WINDOW, min_periods=1)
        .mean()
    )

    # Percentage deviation of 3d volume from baseline.
    # Positive → volume surge; negative → volume drought.
    daily["volume_surge_pct"] = (
        (daily["volume_3d"] - daily["volume_baseline"])
        / daily["volume_baseline"].replace(0, np.nan)
        * 100
    )

    return daily


# RSI period constant
_RSI_PERIOD = 14


def _compute_rsi(daily: pd.DataFrame, period: int = _RSI_PERIOD) -> pd.DataFrame:
    """Append RSI (Relative Strength Index) column to the daily DataFrame.

    Uses Wilder's smoothing method (exponential moving average with alpha=1/period).
    RSI = 100 - (100 / (1 + RS)), where RS = avg_gain / avg_loss over `period` days.

    Adds column:
      - ``rsi`` : float in [0, 100], or NaN where insufficient data.
        RSI < 30 = oversold (potential buy); RSI > 70 = overbought (potential sell).

    Parameters
    ----------
    daily : pd.DataFrame
        Date-indexed DataFrame with a ``price_mean`` column.
    period : int
        Lookback period for RSI calculation (default: 14).

    Returns
    -------
    pd.DataFrame
        The same DataFrame with the ``rsi`` column appended.
    """
    delta = daily["price_mean"].diff()

    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Wilder's smoothing: EMA with alpha = 1/period
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    daily["rsi"] = 100 - (100 / (1 + rs))

    return daily


def _classify_row(row: pd.Series) -> str:
    """Apply the signal logic to a single daily-aggregated row.

    Signal priority (evaluated in order):
      1. INSUFFICIENT DATA — price_mean is NaN (no sales that day).
      2. STRONG BUY        — price is DIP_THRESHOLD below SMA-30 AND
                             3d volume is VOLUME_SURGE_FACTOR above baseline.
      3. BUY               — price is DIP_THRESHOLD below SMA-30 (but no
                             volume confirmation).
      4. STRONG SELL       — price is STRONG_SELL_THRESHOLD above SMA-30.
      5. SELL              — price is _SELL_THRESHOLD above SMA-30.
      6. HOLD              — everything else.

    Parameters
    ----------
    row : pd.Series
        A single row from the fully-annotated daily DataFrame.

    Returns
    -------
    str
        One of the SIGNAL_* constants.
    """
    # No sales on this day — cannot evaluate.
    if pd.isna(row.get("price_mean")):
        return SIGNAL_INSUFFICIENT_DATA

    sma_long_col = f"sma_{SMA_LONG_WINDOW}"
    sma_30 = row.get(sma_long_col)
    pct = row.get("price_vs_sma30_pct")
    vol_surge = row.get("volume_surge_pct")

    # Guard: if SMA-30 is not yet computable, return HOLD rather than garbage.
    if pd.isna(sma_30) or pd.isna(pct):
        return SIGNAL_HOLD

    # --- Dip check ---
    # price_vs_sma30_pct is negative when price is below SMA-30.
    price_is_dipped = pct <= -(DIP_THRESHOLD * 100)      # e.g., -15.0

    # --- Volume confirmation ---
    # volume_surge_pct > 0 means 3d volume exceeds baseline.
    volume_is_surging = (
        (not pd.isna(vol_surge))
        and vol_surge >= (VOLUME_SURGE_FACTOR - 1) * 100  # e.g., 20.0
    )

    # --- Overbought check ---
    price_is_elevated = pct >= (_SELL_THRESHOLD * 100)      # e.g., +15.0
    price_is_very_elevated = pct >= (STRONG_SELL_THRESHOLD * 100)  # +30.0

    # --- RSI confirmation (when available) ---
    rsi = row.get("rsi")
    rsi_oversold = (not pd.isna(rsi)) and rsi < 30
    rsi_overbought = (not pd.isna(rsi)) and rsi > 70

    # --- Signal hierarchy ---
    # RSI can upgrade a BUY to STRONG BUY, or a SELL to STRONG SELL.
    if price_is_dipped and (volume_is_surging or rsi_oversold):
        return SIGNAL_STRONG_BUY

    if price_is_dipped:
        return SIGNAL_BUY

    if price_is_very_elevated or (price_is_elevated and rsi_overbought):
        return SIGNAL_STRONG_SELL

    if price_is_elevated:
        return SIGNAL_SELL

    return SIGNAL_HOLD


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full signal pipeline and return an annotated daily DataFrame.

    This is the main entry point for Module 2. It takes a clean sales
    DataFrame (output of Module 1) and returns a date-indexed DataFrame
    with every intermediate calculation column plus the final ``signal``
    column.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized sales DataFrame from `pokequant.ingestion.normalizer`.

    Returns
    -------
    pd.DataFrame
        Date-indexed DataFrame with columns:
          price_mean, price_low, price_high, volume, num_transactions,
          sma_7, sma_30, price_vs_sma30_pct,
          volume_3d, volume_baseline, volume_surge_pct,
          signal

    Raises
    ------
    ValueError
        If the input DataFrame is empty or missing required columns.
    """
    if df.empty:
        raise ValueError("Cannot generate signals from an empty DataFrame.")

    daily = _aggregate_daily(df)
    daily = _compute_smas(daily)
    daily = _compute_volume_signals(daily)
    daily = _compute_rsi(daily)
    daily["signal"] = daily.apply(_classify_row, axis=1)

    n_buy = (daily["signal"] == SIGNAL_STRONG_BUY).sum()
    n_sell = (daily["signal"].isin([SIGNAL_SELL, SIGNAL_STRONG_SELL])).sum()
    logger.info(
        "Signal generation complete — %d STRONG BUY, %d SELL/STRONG SELL "
        "across %d trading days.",
        n_buy,
        n_sell,
        daily["price_mean"].notna().sum(),
    )

    return daily


def latest_signal(df: pd.DataFrame, card_id: str = "unknown") -> SignalResult:
    """Return the most recent signal evaluation as a structured result.

    Convenience wrapper around `generate_signals` that extracts the last
    row with actual price data and returns it as a `SignalResult` dataclass.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized sales DataFrame from Module 1.
    card_id : str
        Identifier string attached to the result for display purposes.

    Returns
    -------
    SignalResult
        Fully populated result with all signal components.
    """
    daily = generate_signals(df)

    sma_short_col = f"sma_{SMA_SHORT_WINDOW}"
    sma_long_col = f"sma_{SMA_LONG_WINDOW}"

    # Only consider rows where we actually had a sale (price_mean is not NaN).
    tradeable = daily[daily["price_mean"].notna()]

    if tradeable.empty:
        raise ValueError(
            f"Card '{card_id}' has no rows with sales data after aggregation."
        )

    last = tradeable.iloc[-1]

    return SignalResult(
        card_id=card_id,
        signal=str(last["signal"]),
        current_price=float(last["price_mean"]),
        sma_7=float(last[sma_short_col]) if not pd.isna(last[sma_short_col]) else None,
        sma_30=float(last[sma_long_col]) if not pd.isna(last[sma_long_col]) else None,
        price_vs_sma30_pct=(
            float(last["price_vs_sma30_pct"])
            if not pd.isna(last["price_vs_sma30_pct"])
            else None
        ),
        volume_3d=float(last["volume_3d"]),
        volume_baseline=(
            float(last["volume_baseline"])
            if not pd.isna(last["volume_baseline"])
            else None
        ),
        volume_surge_pct=(
            float(last["volume_surge_pct"])
            if not pd.isna(last["volume_surge_pct"])
            else None
        ),
        rsi=(
            round(float(last["rsi"]), 1)
            if not pd.isna(last.get("rsi"))
            else None
        ),
        as_of_date=last.name,  # The DatetimeIndex label is the date.
        metadata={
            "sma_short_window": SMA_SHORT_WINDOW,
            "sma_long_window": SMA_LONG_WINDOW,
            "dip_threshold_pct": DIP_THRESHOLD * 100,
            "volume_surge_required_pct": (VOLUME_SURGE_FACTOR - 1) * 100,
        },
    )


def scan_all_signals(
    card_data: dict[str, "pd.DataFrame"]
) -> dict[str, SignalResult]:
    """Run `latest_signal` over an entire ingested card collection.

    Parameters
    ----------
    card_data : dict[str, pd.DataFrame]
        Output of `pokequant.ingestion.normalizer.ingest_all`.

    Returns
    -------
    dict[str, SignalResult]
        Keys are card_id strings. Cards that fail signal generation are
        logged and omitted from the result.
    """
    results: dict[str, SignalResult] = {}

    for card_id, df in card_data.items():
        try:
            result = latest_signal(df, card_id=card_id)
            results[card_id] = result
        except ValueError as exc:
            logger.error(
                "Could not generate signal for '%s': %s", card_id, exc
            )

    return results


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from pathlib import Path
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s  %(name)s — %(message)s",
    )

    # Re-use the normalizer from Module 1.
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from pokequant.ingestion.normalizer import ingest_all

    sample_path = Path(__file__).parents[2] / "data" / "raw" / "sample_sales.json"
    card_data = ingest_all(sample_path)

    all_signals = scan_all_signals(card_data)

    print("\n" + "=" * 70)
    print("  POKEQUANT — SIGNAL REPORT")
    print("=" * 70)
    for card_id, result in all_signals.items():
        print(f"\n{result}")

    sys.exit(0)
