"""SourceReconciler — merges records from many adapters into one clean list.

Pure function: (records) -> (records, audit). No I/O, no network.
"""
from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from pokequant.sources.fx import to_usd
from pokequant.sources.priority import priority_for
from pokequant.sources.schema import NormalizedSale

logger = logging.getLogger(__name__)


@dataclass
class ReconciliationAudit:
    reconciled_count: int = 0
    by_adapter: dict[str, int] = field(default_factory=dict)
    dropped_outliers: int = 0
    fx_normalized: int = 0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "reconciled_count": self.reconciled_count,
            "by_adapter": dict(self.by_adapter),
            "dropped_outliers": self.dropped_outliers,
            "fx_normalized": self.fx_normalized,
            "warnings": list(self.warnings),
        }


def _iqr_fence(values: list[float]) -> tuple[float, float]:
    """Return (low, high) fence at 1.5x IQR. Requires >=5 values."""
    values = sorted(values)
    n = len(values)
    q1 = statistics.median(values[: n // 2])
    q3 = statistics.median(values[(n + 1) // 2 :])
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def reconcile(
    records: Iterable[NormalizedSale],
    *,
    days: int,
    today: date | None = None,
) -> tuple[list[NormalizedSale], ReconciliationAudit]:
    """Merge, FX-normalize, dedupe, and outlier-flag adapter records.

    Returns (clean_records, audit).
    """
    today = today or datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=days)
    audit = ReconciliationAudit()

    in_window: list[NormalizedSale] = []
    for r in records:
        if r.date < cutoff or r.date > today:
            continue
        in_window.append(r)

    # FX-normalize non-USD to USD by replacing the record with a USD clone
    # (price updated; currency marked USD; original logged in extra).
    fx_normalized: list[NormalizedSale] = []
    for r in in_window:
        if r.currency == "USD":
            fx_normalized.append(r)
            continue
        usd = to_usd(r.price, r.currency)
        if usd is None:
            audit.warnings.append(f"unknown currency: {r.currency} from {r.adapter}")
            fx_normalized.append(r)
            continue
        audit.fx_normalized += 1
        new_extra = {**r.extra, "original_price": r.price, "original_currency": r.currency}
        fx_normalized.append(
            NormalizedSale(
                sale_id=r.sale_id,
                adapter=r.adapter,
                source_type=r.source_type,
                price=usd,
                currency="USD",
                date=r.date,
                condition=r.condition,
                grade=r.grade,
                source_url=r.source_url,
                quantity=r.quantity,
                lot_size=r.lot_size,
                confidence=r.confidence,
                outlier_flag=r.outlier_flag,
                fetched_at=r.fetched_at,
                extra=new_extra,
            )
        )

    # Dedupe: same (round(price,2), date, grade) across adapters — keep highest priority.
    by_key: dict[tuple[float, date, str], NormalizedSale] = {}
    for r in fx_normalized:
        key = (round(r.price, 2), r.date, r.grade)
        incumbent = by_key.get(key)
        if incumbent is None or priority_for(r.adapter) > priority_for(incumbent.adapter):
            by_key[key] = r
    deduped = list(by_key.values())

    # IQR fence over sale records only; mark outliers but do NOT drop.
    sale_records = [r for r in deduped if r.source_type == "sale"]
    if len(sale_records) >= 5:
        lo, hi = _iqr_fence([r.price for r in sale_records])
        flagged: list[NormalizedSale] = []
        for r in deduped:
            if r.source_type == "sale" and (r.price < lo or r.price > hi) and not r.outlier_flag:
                audit.dropped_outliers += 1
                flagged.append(
                    NormalizedSale(
                        sale_id=r.sale_id,
                        adapter=r.adapter,
                        source_type=r.source_type,
                        price=r.price,
                        currency=r.currency,
                        date=r.date,
                        condition=r.condition,
                        grade=r.grade,
                        source_url=r.source_url,
                        quantity=r.quantity,
                        lot_size=r.lot_size,
                        confidence=r.confidence,
                        outlier_flag=True,
                        fetched_at=r.fetched_at,
                        extra=r.extra,
                    )
                )
            else:
                flagged.append(r)
        deduped = flagged

    # Build per-adapter audit counts
    for r in deduped:
        audit.by_adapter[r.adapter] = audit.by_adapter.get(r.adapter, 0) + 1
    audit.reconciled_count = len(deduped)

    return deduped, audit
