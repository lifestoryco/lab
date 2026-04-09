"""
pokequant/db/store.py
----------------------
SQLite Persistence Layer

Provides read/write operations for the three core tables:
  - ``sales``         : individual normalized sale records
  - ``signals``       : historical signal evaluations (one per card per date)
  - ``comps``         : CMC snapshots with metadata

Using sqlite3 from the stdlib keeps the dependency footprint minimal.
All writes use parameterized queries to prevent SQL injection.
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

import pandas as pd

from config import DB_PATH

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DDL — tables are created on first connect if they don't exist.
# ---------------------------------------------------------------------------
_DDL = """
CREATE TABLE IF NOT EXISTS sales (
    sale_id     TEXT PRIMARY KEY,
    card_id     TEXT NOT NULL,
    card_name   TEXT,
    set_name    TEXT,
    language    TEXT DEFAULT 'EN',
    price       REAL NOT NULL,
    date        TEXT NOT NULL,
    condition   TEXT,
    source      TEXT,
    quantity    INTEGER DEFAULT 1,
    price_usd   REAL
);

CREATE INDEX IF NOT EXISTS idx_sales_card_date ON sales (card_id, date);

CREATE TABLE IF NOT EXISTS signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id     TEXT NOT NULL,
    signal_date TEXT NOT NULL,
    signal      TEXT NOT NULL,
    price       REAL,
    sma_7       REAL,
    sma_30      REAL,
    price_vs_sma30_pct REAL,
    volume_3d   REAL,
    volume_baseline REAL,
    volume_surge_pct REAL,
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE (card_id, signal_date)
);

CREATE TABLE IF NOT EXISTS comps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id         TEXT NOT NULL,
    card_name       TEXT,
    cmc             REAL NOT NULL,
    simple_mean     REAL,
    cmc_vs_mean_pct REAL,
    sales_used      INTEGER,
    decay_lambda    REAL,
    confidence      TEXT,
    volatility_score TEXT,
    price_stddev     REAL,
    newest_sale_date TEXT,
    oldest_sale_date TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
"""


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


@contextmanager
def _get_conn(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a sqlite3 connection and commits/rolls back.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file. Created automatically.

    Yields
    ------
    sqlite3.Connection
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row   # Access rows as dict-like objects.
    conn.execute("PRAGMA journal_mode=WAL;")  # Better concurrency.
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_db(db_path: str = DB_PATH) -> None:
    """Create tables if they don't already exist."""
    with _get_conn(db_path) as conn:
        conn.executescript(_DDL)
        # Migrate existing databases that predate volatility columns.
        for col, col_type in [("volatility_score", "TEXT"), ("price_stddev", "REAL")]:
            try:
                conn.execute(f"ALTER TABLE comps ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass  # Column already exists — safe to ignore.
    logger.info("Database initialized at %s.", db_path)


# ---------------------------------------------------------------------------
# Sales table
# ---------------------------------------------------------------------------


def upsert_sales(df: pd.DataFrame, db_path: str = DB_PATH) -> int:
    """Insert or replace rows from a normalized sales DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Clean DataFrame from `normalizer.ingest_card`.

    Returns
    -------
    int
        Number of rows written.
    """
    initialize_db(db_path)

    records = df.to_dict(orient="records")
    sql = """
        INSERT OR REPLACE INTO sales
            (sale_id, card_id, card_name, set_name, language,
             price, date, condition, source, quantity, price_usd)
        VALUES
            (:sale_id, :card_id, :card_name, :set_name, :language,
             :price, :date, :condition, :source, :quantity, :price_usd)
    """

    # Convert Timestamps to ISO strings before writing.
    for rec in records:
        if hasattr(rec.get("date"), "isoformat"):
            rec["date"] = rec["date"].isoformat()
        rec.setdefault("price_usd", rec.get("price"))

    with _get_conn(db_path) as conn:
        conn.executemany(sql, records)

    logger.info("Upserted %d sale record(s) into database.", len(records))
    return len(records)


def load_sales(card_id: str, db_path: str = DB_PATH) -> pd.DataFrame:
    """Load all sales for a given card_id from the database.

    Returns
    -------
    pd.DataFrame
        Sorted by date ascending, or empty DataFrame if no rows found.
    """
    with _get_conn(db_path) as conn:
        cursor = conn.execute(
            "SELECT * FROM sales WHERE card_id = ? ORDER BY date ASC",
            (card_id,),
        )
        rows = cursor.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    df["date"] = pd.to_datetime(df["date"])
    return df


# ---------------------------------------------------------------------------
# Signals table
# ---------------------------------------------------------------------------


def upsert_signal(
    card_id: str,
    signal_date: str,
    signal: str,
    price: float | None = None,
    sma_7: float | None = None,
    sma_30: float | None = None,
    price_vs_sma30_pct: float | None = None,
    volume_3d: float | None = None,
    volume_baseline: float | None = None,
    volume_surge_pct: float | None = None,
    db_path: str = DB_PATH,
) -> None:
    """Write a signal evaluation row to the database."""
    initialize_db(db_path)

    sql = """
        INSERT OR REPLACE INTO signals
            (card_id, signal_date, signal, price, sma_7, sma_30,
             price_vs_sma30_pct, volume_3d, volume_baseline, volume_surge_pct)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _get_conn(db_path) as conn:
        conn.execute(
            sql,
            (
                card_id, signal_date, signal, price, sma_7, sma_30,
                price_vs_sma30_pct, volume_3d, volume_baseline, volume_surge_pct,
            ),
        )
    logger.debug("Saved signal '%s' for %s on %s.", signal, card_id, signal_date)


# ---------------------------------------------------------------------------
# Comps table
# ---------------------------------------------------------------------------


def save_comp(comp_result: "CompResult", db_path: str = DB_PATH) -> None:  # noqa: F821
    """Persist a CompResult snapshot to the database."""
    initialize_db(db_path)

    sql = """
        INSERT INTO comps
            (card_id, card_name, cmc, simple_mean, cmc_vs_mean_pct,
             sales_used, decay_lambda, confidence, volatility_score,
             price_stddev, newest_sale_date, oldest_sale_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _get_conn(db_path) as conn:
        conn.execute(
            sql,
            (
                comp_result.card_id,
                comp_result.card_name,
                comp_result.cmc,
                comp_result.simple_mean,
                comp_result.cmc_vs_mean_pct,
                comp_result.sales_used,
                comp_result.decay_lambda,
                comp_result.confidence,
                comp_result.volatility_score,
                comp_result.price_stddev,
                comp_result.newest_sale_date.isoformat()
                if comp_result.newest_sale_date
                else None,
                comp_result.oldest_sale_date.isoformat()
                if comp_result.oldest_sale_date
                else None,
            ),
        )
    logger.debug("Saved comp for '%s': CMC=$%.2f.", comp_result.card_id, comp_result.cmc)
