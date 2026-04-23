"""NormalizedSale — the invariant every adapter must emit."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

SourceType = Literal["sale", "market_estimate", "pop_report", "meta_signal"]
Currency = Literal["USD", "EUR", "GBP", "JPY"]
Grade = Literal[
    "raw",
    "psa10", "psa9", "psa8",
    "bgs10", "bgs9.5",
    "cgc10", "cgc9",
]

VALID_CURRENCIES: frozenset[str] = frozenset({"USD", "EUR", "GBP", "JPY"})
VALID_GRADES: frozenset[str] = frozenset({
    "raw", "psa10", "psa9", "psa8", "bgs10", "bgs9.5", "cgc10", "cgc9",
})
VALID_SOURCE_TYPES: frozenset[str] = frozenset({
    "sale", "market_estimate", "pop_report", "meta_signal",
})


@dataclass(frozen=True)
class NormalizedSale:
    sale_id: str
    adapter: str
    source_type: SourceType

    price: float
    currency: Currency
    date: date
    condition: str
    grade: Grade

    source_url: str
    quantity: int = 1
    lot_size: int = 1

    confidence: float = 1.0
    outlier_flag: bool = False
    fetched_at: float | None = None

    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sale_id": self.sale_id,
            "adapter": self.adapter,
            "source_type": self.source_type,
            "price": self.price,
            "currency": self.currency,
            "date": self.date.isoformat(),
            "condition": self.condition,
            "grade": self.grade,
            "source_url": self.source_url,
            "quantity": self.quantity,
            "lot_size": self.lot_size,
            "confidence": self.confidence,
            "outlier_flag": self.outlier_flag,
            "fetched_at": self.fetched_at,
            "extra": dict(self.extra),
        }
