"""
pokequant/comps/generator.py
------------------------------
Module 5 — Comp Generation (Weighted Market Comparables)

Responsibilities:
  1. Accept a card_id and retrieve its last N verified sales from the
     normalized DataFrame (or a direct list of sale dicts).
  2. Apply exponential decay weighting so recent sales carry more
     influence than older ones: weight_i = exp(-λ · i), where i=0 is
     the MOST recent sale.
  3. Compute the weighted-average price as the Current Market Comp (CMC).
  4. Return a structured CompResult with confidence metadata.

Why exponential decay?
  TCG prices are non-stationary — a card may have spiked due to a
  tournament result last week, making 30-day-old comps misleading.
  Exponential decay lets the most recent sale exert the strongest pull
  while still using all available data points to smooth single outliers.

  Weight formula:
      w_i = exp(−λ · i),  i = 0 (newest) … N-1 (oldest)

  Weighted average:
      CMC = Σ(price_i · w_i) / Σ(w_i)

  At λ=0.3 (default):
      Sale 0 (today):    weight ≈ 1.000  (100%)
      Sale 1 (prev):     weight ≈ 0.741  ( 74%)
      Sale 2:            weight ≈ 0.549  ( 55%)
      Sale 5:            weight ≈ 0.223  ( 22%)
      Sale 9 (oldest):   weight ≈ 0.067  (  7%)

  Increasing λ makes it more recency-biased; λ=0 produces a plain mean.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from config import COMP_SALES_LIMIT, DECAY_LAMBDA

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


@dataclass
class SalePoint:
    """A single verified sale used in comp calculation."""
    sale_id: str
    price: float
    date: pd.Timestamp
    condition: str
    source: str
    weight: float = 0.0     # Populated by the generator; 0.0 before assignment.


@dataclass
class CompResult:
    """Structured output of the comp generator.

    Attributes
    ----------
    card_id : str
        Identifier of the evaluated card.
    card_name : str
        Human-readable card name.
    cmc : float
        Current Market Comp — the exponentially-weighted average price.
    simple_mean : float
        Un-weighted arithmetic mean of the same sales (for reference).
    cmc_vs_mean_pct : float
        Percentage difference between CMC and simple mean.
        Positive = recent sales dragged comp above average (rising market).
        Negative = recent sales are softer than the window average.
    sales_used : int
        Number of sale records included in the calculation.
    decay_lambda : float
        The λ value used for weighting.
    newest_sale_date : pd.Timestamp
        Date of the most recent sale in the comp window.
    oldest_sale_date : pd.Timestamp
        Date of the oldest sale in the comp window.
    sales : list[SalePoint]
        The individual sale records with their assigned weights (newest first).
    confidence : str
        "HIGH", "MEDIUM", or "LOW" based on sales count and date spread.
    volatility_score : str
        "HIGH", "MEDIUM", or "LOW" based on coefficient of variation
        (stddev / mean). HIGH = price is swinging. LOW = price is stable.
    price_stddev : float
        Standard deviation of raw sale prices in the comp window.
    """

    card_id: str
    card_name: str
    cmc: float
    simple_mean: float
    cmc_vs_mean_pct: float
    sales_used: int
    decay_lambda: float
    newest_sale_date: pd.Timestamp
    oldest_sale_date: pd.Timestamp
    sales: list[SalePoint] = field(default_factory=list)
    confidence: str = "UNKNOWN"
    volatility_score: str = "UNKNOWN"
    price_stddev: float = 0.0

    def __str__(self) -> str:  # pragma: no cover
        lines = [
            f"\n{'='*60}",
            f"  COMP REPORT — {self.card_name} ({self.card_id})",
            f"  {'='*58}",
            f"  Current Market Comp (CMC): ${self.cmc:.2f}",
            f"  Simple Mean:               ${self.simple_mean:.2f}",
            f"  CMC vs Mean:               {self.cmc_vs_mean_pct:+.1f}%",
            f"  Confidence:                {self.confidence}",
            f"  Sales window:              {self.oldest_sale_date.date()} "
            f"→ {self.newest_sale_date.date()}",
            f"  Sales used (λ={self.decay_lambda}):     {self.sales_used}",
            "",
            "  Sale Detail (newest → oldest):",
        ]
        for sp in self.sales:
            lines.append(
                f"    {sp.date.date()}  ${sp.price:>8.2f}  "
                f"{sp.condition:<4}  {sp.source:<12}  "
                f"weight={sp.weight:.4f}"
            )
        lines.append("=" * 60)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _assign_decay_weights(
    sale_points: list[SalePoint],
    lam: float,
) -> list[SalePoint]:
    """Return a new list of SalePoints with decay weights assigned.

    Does NOT mutate the input list. The list must be ordered NEWEST FIRST
    (index 0 = most recent sale).
    """
    if lam < 0:
        raise ValueError(f"Decay lambda must be ≥ 0, got {lam}.")

    return [
        SalePoint(
            sale_id=sp.sale_id,
            price=sp.price,
            date=sp.date,
            condition=sp.condition,
            source=sp.source,
            weight=math.exp(-lam * i),
        )
        for i, sp in enumerate(sale_points)
    ]


def _compute_weighted_average(sale_points: list[SalePoint]) -> float:
    """Compute the weight-normalized average price.

    Parameters
    ----------
    sale_points : list[SalePoint]
        Each must have ``.price`` and ``.weight`` set.

    Returns
    -------
    float
        Weighted average price.

    Raises
    ------
    ValueError
        If all weights sum to zero (degenerate case).
    """
    total_weight = sum(sp.weight for sp in sale_points)
    if total_weight == 0:
        raise ValueError(
            "All sale weights are zero. Cannot compute weighted average."
        )

    weighted_sum = sum(sp.price * sp.weight for sp in sale_points)
    return weighted_sum / total_weight


def _assess_confidence(sales_used: int, date_spread_days: int) -> str:
    """Assign a qualitative confidence label.

    Rules:
      - HIGH:   ≥ 7 sales AND date spread ≤ 14 days (fresh, dense data)
      - MEDIUM: ≥ 4 sales AND date spread ≤ 30 days (adequate volume, not stale)
      - LOW:    Anything else (sparse or stale)

    Parameters
    ----------
    sales_used : int
        Number of sales included in the comp.
    date_spread_days : int
        Calendar days between oldest and newest sale.

    Returns
    -------
    str
        "HIGH", "MEDIUM", or "LOW".
    """
    if sales_used >= 7 and date_spread_days <= 14:
        return "HIGH"
    if sales_used >= 4 and date_spread_days <= 30:
        return "MEDIUM"
    return "LOW"


def _assess_volatility(prices: list[float]) -> tuple[str, float]:
    """Compute volatility score from raw price list.

    Uses the coefficient of variation (stddev / mean) so the score is
    relative to the card's price level (a $1 stddev means different things
    for a $5 card vs a $500 card).

    Thresholds:
      HIGH:   CV > 0.15  (>15% — price is swinging unpredictably)
      MEDIUM: CV > 0.07  ( 7-15% — moderate movement)
      LOW:    CV ≤ 0.07  (stable, tight price range)

    Parameters
    ----------
    prices : list[float]
        Raw prices from the comp window (not decay-weighted).

    Returns
    -------
    tuple[str, float]
        (volatility_label, stddev)
    """
    if len(prices) < 2:
        return "UNKNOWN", 0.0

    mean = float(np.mean(prices))
    stddev = float(np.std(prices, ddof=1))  # Sample std dev (ddof=1)

    if mean == 0:
        return "UNKNOWN", stddev

    cv = stddev / mean

    if cv > 0.15:
        label = "HIGH"
    elif cv > 0.07:
        label = "MEDIUM"
    else:
        label = "LOW"

    return label, round(stddev, 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_comp(
    df: pd.DataFrame,
    card_id: str,
    n_sales: int = COMP_SALES_LIMIT,
    decay_lambda: float = DECAY_LAMBDA,
) -> CompResult:
    """Generate a weighted market comp from a clean sales DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized sales DataFrame from `pokequant.ingestion.normalizer`.
        Must contain: sale_id, price, date, condition, source columns.
    card_id : str
        The card identifier — used for display and filtering.
    n_sales : int
        Maximum number of recent sales to include.
    decay_lambda : float
        Exponential decay constant λ.

    Returns
    -------
    CompResult
        Full comp result with weighted CMC and metadata.

    Raises
    ------
    ValueError
        If the DataFrame is empty or doesn't have enough rows to generate
        a meaningful comp.
    """
    if df.empty:
        raise ValueError(f"Cannot generate comp for '{card_id}': DataFrame is empty.")

    # Required columns for comp generation.
    required = {"sale_id", "price", "date", "condition", "source"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"DataFrame is missing required columns: {missing}"
        )

    # Sort newest-first and take the N most recent.
    df_sorted = df.sort_values("date", ascending=False).head(n_sales).copy()

    if df_sorted.empty:
        raise ValueError(
            f"No sales records available for card '{card_id}' after filtering."
        )

    card_name = (
        df_sorted["card_name"].iloc[0]
        if "card_name" in df_sorted.columns
        else card_id
    )

    # Convert to SalePoint objects.
    sale_points: list[SalePoint] = [
        SalePoint(
            sale_id=str(row["sale_id"]),
            price=float(row["price"]),
            date=pd.Timestamp(row["date"]),
            condition=str(row["condition"]),
            source=str(row["source"]),
        )
        for row in df_sorted.to_dict(orient="records")
    ]

    # Assign decay weights (index 0 = newest = highest weight).
    sale_points = _assign_decay_weights(sale_points, lam=decay_lambda)

    # Weighted average (CMC).
    cmc = _compute_weighted_average(sale_points)

    # Simple (un-weighted) mean for comparison.
    simple_mean = float(np.mean([sp.price for sp in sale_points]))

    # Percentage difference: positive = recent prices above average.
    cmc_vs_mean_pct = ((cmc / simple_mean) - 1) * 100 if simple_mean != 0 else 0.0

    # Date range metadata.
    newest_date = sale_points[0].date
    oldest_date = sale_points[-1].date
    date_spread_days = (newest_date - oldest_date).days

    confidence = _assess_confidence(len(sale_points), date_spread_days)

    # Compute volatility from the raw price list (unweighted — we want the
    # true price spread, not a decay-smoothed view).
    raw_prices = [sp.price for sp in sale_points]
    volatility_score, price_stddev = _assess_volatility(raw_prices)

    logger.info(
        "Comp for '%s': CMC=$%.2f (simple mean=$%.2f, Δ%+.1f%%), "
        "%d sales, λ=%.2f, confidence=%s, volatility=%s",
        card_id,
        cmc,
        simple_mean,
        cmc_vs_mean_pct,
        len(sale_points),
        decay_lambda,
        confidence,
        volatility_score,
    )

    return CompResult(
        card_id=card_id,
        card_name=card_name,
        cmc=round(cmc, 2),
        simple_mean=round(simple_mean, 2),
        cmc_vs_mean_pct=round(cmc_vs_mean_pct, 2),
        sales_used=len(sale_points),
        decay_lambda=decay_lambda,
        newest_sale_date=newest_date,
        oldest_sale_date=oldest_date,
        sales=sale_points,
        confidence=confidence,
        volatility_score=volatility_score,
        price_stddev=price_stddev,
    )


def generate_comp_from_list(
    sales: list[dict[str, Any]],
    card_id: str,
    card_name: str = "",
    n_sales: int = COMP_SALES_LIMIT,
    decay_lambda: float = DECAY_LAMBDA,
) -> CompResult:
    """Generate a comp directly from a list of sale dicts (no DataFrame required).

    This is a convenience wrapper for use cases where you already have
    raw sale records (e.g., freshly scraped from an API) without going
    through the full ingestion pipeline.

    Parameters
    ----------
    sales : list[dict]
        Each dict must have 'sale_id', 'price', 'date', 'condition', 'source'.
    card_id : str
        Card identifier.
    card_name : str
        Human-readable name (optional; defaults to card_id).
    n_sales : int
        Maximum recent sales to use.
    decay_lambda : float
        Decay constant.

    Returns
    -------
    CompResult
    """
    if not sales:
        raise ValueError(
            f"Cannot generate comp for '{card_id}': sales list is empty."
        )

    # Build a minimal DataFrame and delegate to generate_comp.
    rows: list[dict[str, Any]] = []
    for idx, sale in enumerate(sales):
        for required_key in ("sale_id", "price", "date", "condition", "source"):
            if required_key not in sale:
                raise KeyError(
                    f"Sale #{idx} is missing required key '{required_key}'."
                )
        try:
            rows.append(
                {
                    "sale_id": str(sale["sale_id"]),
                    "card_id": card_id,
                    "card_name": card_name or card_id,
                    "price": float(sale["price"]),
                    "date": pd.to_datetime(sale["date"]),
                    "condition": str(sale["condition"]),
                    "source": str(sale["source"]),
                }
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Cannot parse sale #{idx} for card '{card_id}': {exc}"
            ) from exc

    df = pd.DataFrame(rows)
    return generate_comp(df, card_id=card_id, n_sales=n_sales, decay_lambda=decay_lambda)


# ---------------------------------------------------------------------------
# Smoke-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import logging
    from pathlib import Path

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-8s  %(name)s — %(message)s",
    )

    sys.path.insert(0, str(Path(__file__).parents[2]))
    from pokequant.ingestion.normalizer import ingest_all

    sample_path = Path(__file__).parents[2] / "data" / "raw" / "sample_sales.json"
    card_data = ingest_all(sample_path)

    for card_id, df in card_data.items():
        comp = generate_comp(df, card_id=card_id)
        print(comp)
