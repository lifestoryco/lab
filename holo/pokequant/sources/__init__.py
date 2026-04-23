"""Multi-source price intelligence platform — unified adapter framework.

Public surface:
    from pokequant.sources import registry, NormalizedSale, SourceAdapter
"""
from __future__ import annotations

from pokequant.sources.schema import (
    Currency,
    Grade,
    NormalizedSale,
    SourceType,
)
from pokequant.sources.base import SourceAdapter
from pokequant.sources.exceptions import (
    AdapterNotConfigured,
    AdapterTimeout,
    InvalidSaleRecord,
)
from pokequant.sources.registry import SourceRegistry, registry

__all__ = [
    "AdapterNotConfigured",
    "AdapterTimeout",
    "Currency",
    "Grade",
    "InvalidSaleRecord",
    "NormalizedSale",
    "SourceAdapter",
    "SourceRegistry",
    "SourceType",
    "registry",
]
