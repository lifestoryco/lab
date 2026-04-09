"""
pokequant/ingestion/normalizer.py
----------------------------------
Module 1 — Data Ingestion & Normalization

Responsibilities:
  1. Load raw sales JSON payloads (eBay / TCGPlayer format).
  2. Validate required fields and coerce types.
  3. Remove extreme outliers using Interquartile Range (IQR) fencing.
  4. Normalize each card's sales history into a clean, time-indexed
     Pandas DataFrame ready for downstream quantitative analysis.

Design notes:
  - All functions are pure (no side effects) except `load_json_file`.
  - IQR fencing uses the standard Tukey method: [Q1 - k·IQR, Q3 + k·IQR].
  - The multiplier `k` and hard floor/ceiling are pulled from config.py so
    they can be tuned without touching this file.
  - Every public function raises descriptive ValueError / TypeError so
    callers know exactly what went wrong.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import (
    HARD_PRICE_CEILING,
    HARD_PRICE_FLOOR,
    IQR_MULTIPLIER,
)

# ---------------------------------------------------------------------------
# Module-level logger — callers can configure the root logger as desired.
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required keys that every raw sale record must contain.
# ---------------------------------------------------------------------------
_REQUIRED_SALE_KEYS: frozenset[str] = frozenset(
    {"sale_id", "price", "date", "condition", "source", "quantity"}
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_json_file(filepath: str | Path) -> list[dict[str, Any]]:
    """Load a raw sales JSON file from disk.

    The file must contain a JSON array where each element represents one
    card's sales history (see data/raw/sample_sales.json for the schema).

    Parameters
    ----------
    filepath : str or Path
        Absolute or relative path to the JSON file.

    Returns
    -------
    list[dict]
        Parsed JSON payload as a Python list of dicts.

    Raises
    ------
    FileNotFoundError
        If the file does not exist at the given path.
    ValueError
        If the JSON is valid but the top-level structure is not a list.
    json.JSONDecodeError
        If the file content is not valid JSON.
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"Sales data file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    # Validate top-level shape — must be a list of card objects.
    if not isinstance(payload, list):
        raise ValueError(
            f"Expected a JSON array at the top level of {path}; "
            f"got {type(payload).__name__}."
        )

    logger.info("Loaded %d card record(s) from %s.", len(payload), path)
    return payload


def extract_raw_dataframe(card_record: dict[str, Any]) -> pd.DataFrame:
    """Convert a single card's raw JSON record into a Pandas DataFrame.

    Each row in the resulting DataFrame corresponds to one sale transaction.
    Performs lightweight type coercion (price → float, date → datetime,
    quantity → int) but does NOT filter outliers — that is left to
    `apply_iqr_filter`.

    Parameters
    ----------
    card_record : dict
        One element from the top-level JSON array, containing at minimum
        the keys ``card_id``, ``name``, ``set``, and ``sales``.

    Returns
    -------
    pd.DataFrame
        Columns: sale_id, card_id, card_name, set_name, language,
                 price, date, condition, source, quantity.
        Index: RangeIndex (reset — sorting happens in `normalize`).

    Raises
    ------
    KeyError
        If the card record is missing ``card_id``, ``name``, or ``sales``.
    ValueError
        If any individual sale record is missing required keys, or if a
        price / quantity value cannot be coerced to a number.
    """
    # --- Guard: required top-level card keys ---
    for required_key in ("card_id", "name", "sales"):
        if required_key not in card_record:
            raise KeyError(
                f"Card record is missing required key '{required_key}': "
                f"{card_record}"
            )

    card_id: str = card_record["card_id"]
    card_name: str = card_record["name"]
    set_name: str = card_record.get("set", "Unknown Set")
    language: str = card_record.get("language", "EN")

    raw_sales: list[dict] = card_record["sales"]

    if not isinstance(raw_sales, list) or len(raw_sales) == 0:
        raise ValueError(
            f"Card '{card_id}' has no sales records or 'sales' is not a list."
        )

    rows: list[dict[str, Any]] = []

    for idx, sale in enumerate(raw_sales):
        # Validate that all required sale keys are present.
        missing = _REQUIRED_SALE_KEYS - sale.keys()
        if missing:
            logger.warning(
                "Sale #%d for card '%s' is missing keys %s — skipping.",
                idx,
                card_id,
                missing,
            )
            continue  # Skip malformed records rather than crashing the pipeline.

        # --- Type coercion with explicit error messages ---
        try:
            price = float(sale["price"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Cannot convert price '{sale['price']}' to float "
                f"in sale '{sale.get('sale_id', idx)}' for card '{card_id}'."
            ) from exc

        try:
            quantity = int(sale["quantity"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Cannot convert quantity '{sale['quantity']}' to int "
                f"in sale '{sale.get('sale_id', idx)}' for card '{card_id}'."
            ) from exc

        try:
            date = pd.to_datetime(sale["date"])
        except Exception as exc:
            raise ValueError(
                f"Cannot parse date '{sale['date']}' in sale "
                f"'{sale.get('sale_id', idx)}' for card '{card_id}'."
            ) from exc

        rows.append(
            {
                "sale_id": str(sale["sale_id"]),
                "card_id": card_id,
                "card_name": card_name,
                "set_name": set_name,
                "language": language,
                "price": price,
                "date": date,
                "condition": str(sale["condition"]),
                "source": str(sale["source"]),
                "quantity": quantity,
            }
        )

    if not rows:
        raise ValueError(
            f"Card '{card_id}' produced zero valid sale rows after parsing."
        )

    df = pd.DataFrame(rows)
    logger.debug(
        "Extracted %d raw sale rows for card '%s'.", len(df), card_id
    )
    return df


def apply_iqr_filter(
    df: pd.DataFrame,
    multiplier: float = IQR_MULTIPLIER,
    hard_floor: float = HARD_PRICE_FLOOR,
    hard_ceiling: float = HARD_PRICE_CEILING,
) -> pd.DataFrame:
    """Remove price outliers using Tukey's IQR fencing method.

    Two layers of defence:
      1. Hard absolute floor/ceiling — reject physically impossible prices
         (e.g., $99,999 fake listings, $0.01 test transactions) BEFORE the
         IQR is computed so they don't skew the quartiles.
      2. IQR fence — standard Tukey [Q1 - k·IQR, Q3 + k·IQR] with the
         multiplier `k` configurable in config.py.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a ``price`` column (float).
    multiplier : float
        The Tukey fence multiplier (default 1.5 from config).
    hard_floor : float
        Absolute minimum price to keep. Anything below is dropped first.
    hard_ceiling : float
        Absolute maximum price to keep. Anything above is dropped first.

    Returns
    -------
    pd.DataFrame
        A copy of the input with outlier rows removed and a reset index.
        An ``outlier_removed`` column is NOT added — the rows are gone.

    Raises
    ------
    ValueError
        If the DataFrame has no ``price`` column or if the filtered result
        is empty (all records were outliers).
    """
    if "price" not in df.columns:
        raise ValueError("DataFrame must contain a 'price' column.")

    n_before = len(df)

    # --- Stage 1: Hard price bounds (remove before IQR so they don't bias Q1/Q3) ---
    df_filtered = df[
        (df["price"] >= hard_floor) & (df["price"] <= hard_ceiling)
    ].copy()

    n_hard_removed = n_before - len(df_filtered)
    if n_hard_removed > 0:
        logger.info(
            "Hard price bounds removed %d record(s) outside [%.2f, %.2f].",
            n_hard_removed,
            hard_floor,
            hard_ceiling,
        )

    # Edge case: if we're left with fewer than 4 records, IQR is unreliable.
    if len(df_filtered) < 4:
        logger.warning(
            "Only %d record(s) remain after hard-bound filtering — "
            "skipping IQR step (insufficient data).",
            len(df_filtered),
        )
        if df_filtered.empty:
            raise ValueError(
                "All records were removed by hard price bounds. "
                "Check your data source."
            )
        return df_filtered.reset_index(drop=True)

    # --- Stage 2: IQR fencing ---
    q1: float = df_filtered["price"].quantile(0.25)
    q3: float = df_filtered["price"].quantile(0.75)
    iqr: float = q3 - q1

    lower_fence: float = q1 - multiplier * iqr
    upper_fence: float = q3 + multiplier * iqr

    logger.debug(
        "IQR stats — Q1=%.2f, Q3=%.2f, IQR=%.2f, "
        "fence=[%.2f, %.2f].",
        q1,
        q3,
        iqr,
        lower_fence,
        upper_fence,
    )

    mask = (df_filtered["price"] >= lower_fence) & (
        df_filtered["price"] <= upper_fence
    )
    df_clean = df_filtered[mask].copy()

    n_iqr_removed = len(df_filtered) - len(df_clean)
    if n_iqr_removed > 0:
        logger.info(
            "IQR filter removed %d outlier record(s) outside [%.2f, %.2f].",
            n_iqr_removed,
            lower_fence,
            upper_fence,
        )

    if df_clean.empty:
        raise ValueError(
            "IQR filtering removed ALL records — the dataset may be too "
            "small or the prices too dispersed. Lower IQR_MULTIPLIER or "
            "review the data."
        )

    logger.info(
        "Outlier filter: started=%d, removed=%d, remaining=%d.",
        n_before,
        n_before - len(df_clean),
        len(df_clean),
    )

    return df_clean.reset_index(drop=True)


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Sort, de-duplicate, and enrich a cleaned sales DataFrame.

    This is the final normalization step applied after IQR filtering.
    It produces a time-indexed, analysis-ready DataFrame.

    Operations performed (in order):
      1. Sort by ``date`` ascending so rolling windows work correctly.
      2. Drop duplicate ``sale_id`` values (keep first occurrence).
      3. Add a ``price_usd`` alias column (identity — placeholder for
         future FX conversion).
      4. Reset index so row numbers reflect the sorted order.

    Parameters
    ----------
    df : pd.DataFrame
        A filtered DataFrame from `apply_iqr_filter`.

    Returns
    -------
    pd.DataFrame
        Normalized, sorted DataFrame with a clean RangeIndex.
    """
    # Sort chronologically — mandatory for rolling SMA calculations.
    df_sorted = df.sort_values("date", ascending=True).copy()

    # Drop duplicate sale IDs (can occur if raw feeds overlap).
    n_before = len(df_sorted)
    df_sorted.drop_duplicates(subset=["sale_id"], keep="first", inplace=True)
    n_dupes = n_before - len(df_sorted)
    if n_dupes > 0:
        logger.info("Dropped %d duplicate sale_id row(s).", n_dupes)

    # Alias column — future-proof for multi-currency support.
    df_sorted["price_usd"] = df_sorted["price"]

    return df_sorted.reset_index(drop=True)


def ingest_card(card_record: dict[str, Any]) -> pd.DataFrame:
    """Full ingestion pipeline for a single card record.

    Convenience wrapper that chains:
      extract_raw_dataframe → apply_iqr_filter → normalize

    Parameters
    ----------
    card_record : dict
        One element from the top-level sales JSON array.

    Returns
    -------
    pd.DataFrame
        Clean, normalized, time-sorted sales DataFrame for the card.
    """
    raw_df = extract_raw_dataframe(card_record)
    filtered_df = apply_iqr_filter(raw_df)
    return normalize(filtered_df)


def ingest_all(filepath: str | Path) -> dict[str, pd.DataFrame]:
    """Ingest an entire sales JSON file, returning one DataFrame per card.

    Parameters
    ----------
    filepath : str or Path
        Path to the raw JSON file (see data/raw/sample_sales.json).

    Returns
    -------
    dict[str, pd.DataFrame]
        Keys are ``card_id`` strings. Values are clean, normalized DataFrames.
        Cards that fail ingestion are logged and skipped rather than crashing
        the entire pipeline.
    """
    payload = load_json_file(filepath)
    results: dict[str, pd.DataFrame] = {}

    for record in payload:
        card_id = record.get("card_id", "<unknown>")
        try:
            df = ingest_card(record)
            results[card_id] = df
            logger.info(
                "Successfully ingested card '%s' — %d clean sales.",
                card_id,
                len(df),
            )
        except (KeyError, ValueError) as exc:
            # Log and continue — one bad card should not block the whole batch.
            logger.error(
                "Failed to ingest card '%s': %s", card_id, exc
            )

    logger.info(
        "Ingestion complete: %d / %d card(s) processed successfully.",
        len(results),
        len(payload),
    )
    return results


# ---------------------------------------------------------------------------
# Quick smoke-test (run directly: python -m pokequant.ingestion.normalizer)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)-8s  %(name)s — %(message)s",
    )

    sample_path = Path(__file__).parents[2] / "data" / "raw" / "sample_sales.json"
    card_data = ingest_all(sample_path)

    for cid, frame in card_data.items():
        print(f"\n{'='*60}")
        print(f"  Card: {cid}")
        print(f"  Sales after cleaning: {len(frame)}")
        print(frame[["date", "price", "condition", "source", "quantity"]].to_string(index=False))

    sys.exit(0)
