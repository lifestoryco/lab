"""Multi-source price intelligence platform — unified adapter framework.

Public surface:
    from pokequant.sources import registry, NormalizedSale, SourceAdapter
    from pokequant.sources import LAST_AUDIT
"""
from __future__ import annotations

from contextvars import ContextVar

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

# Carries the most recent ReconciliationAudit back to API handlers when
# fetch_sales() went through the registry path. Handlers consume by:
#     from pokequant.sources import LAST_AUDIT
#     audit = LAST_AUDIT.get()
#     if audit is not None: response["reconciliation_audit"] = audit.to_dict()
LAST_AUDIT: ContextVar = ContextVar("LAST_AUDIT", default=None)

__all__ = [
    "AdapterNotConfigured",
    "AdapterTimeout",
    "Currency",
    "Grade",
    "InvalidSaleRecord",
    "LAST_AUDIT",
    "NormalizedSale",
    "SourceAdapter",
    "SourceRegistry",
    "SourceType",
    "registry",
]
