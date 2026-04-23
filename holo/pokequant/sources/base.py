"""SourceAdapter ABC — the contract every data source must implement."""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Sequence

from pokequant.sources.schema import Currency, Grade, NormalizedSale


class SourceAdapter(ABC):
    """One adapter per data source. Stateless; caching lives in the registry."""

    name: str
    enabled_by_default: bool = True
    priority: int = 0
    currency: Currency = "USD"

    @abstractmethod
    def supports_grade(self, grade: Grade) -> bool: ...

    @abstractmethod
    def fetch(
        self, card_name: str, *, days: int, grade: Grade
    ) -> Sequence[NormalizedSale]: ...

    @abstractmethod
    def health_check(self) -> dict:
        """Return {"ok": bool, "latency_ms": float, "error": str | None}.

        Must not raise. Called by /api?action=health.
        """
        ...

    def is_configured(self) -> bool:
        """Env-var feature flag. HOLO_ADAPTER_<NAME>=0 disables."""
        env_key = f"HOLO_ADAPTER_{self.name.upper()}"
        override = os.environ.get(env_key)
        if override == "0":
            return False
        if override == "1":
            return True
        return self.enabled_by_default
