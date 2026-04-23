"""SourceRegistry — discovers adapters, fans out fetches, enforces schema."""
from __future__ import annotations

import importlib
import json
import logging
import pkgutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from pokequant.sources.base import SourceAdapter
from pokequant.sources.exceptions import InvalidSaleRecord
from pokequant.sources.schema import (
    VALID_CURRENCIES,
    VALID_GRADES,
    VALID_SOURCE_TYPES,
    Grade,
    NormalizedSale,
)

logger = logging.getLogger(__name__)

_MAX_PRICE = 1_000_000.0
_ADAPTER_TIMEOUT_S = 12.0


def _validate(r: NormalizedSale) -> None:
    if r.price <= 0 or r.price >= _MAX_PRICE:
        raise InvalidSaleRecord(f"price out of bounds: {r.price} ({r.adapter})")
    if r.currency not in VALID_CURRENCIES:
        raise InvalidSaleRecord(f"unknown currency: {r.currency} ({r.adapter})")
    if r.grade not in VALID_GRADES:
        raise InvalidSaleRecord(f"unknown grade: {r.grade} ({r.adapter})")
    if r.source_type not in VALID_SOURCE_TYPES:
        raise InvalidSaleRecord(f"unknown source_type: {r.source_type} ({r.adapter})")
    if r.source_type == "sale" and r.condition == "mixed":
        raise InvalidSaleRecord(f"sale type forbids mixed condition ({r.adapter})")
    if r.condition == "mixed" and r.source_type != "market_estimate":
        raise InvalidSaleRecord(
            f"mixed condition only allowed on market_estimate ({r.adapter})"
        )
    if r.lot_size > 1 and r.source_type != "sale":
        raise InvalidSaleRecord(f"lot_size>1 only valid on sale records ({r.adapter})")


def _emit_metric(event: str, **fields) -> None:
    payload = {"ts": time.time(), "event": event, **fields}
    print(json.dumps(payload, default=str), file=sys.stderr)


class SourceRegistry:
    def __init__(self) -> None:
        self._adapters: list[SourceAdapter] = []
        # RLock — discover() grabs this while adapter modules re-enter via register().
        self._lock = threading.RLock()
        self._discovered = False

    def register(self, adapter: SourceAdapter) -> None:
        with self._lock:
            if not any(a.name == adapter.name for a in self._adapters):
                self._adapters.append(adapter)

    def discover(self) -> None:
        """Auto-import every pokequant.sources.adapters.* module once."""
        if self._discovered:
            return
        with self._lock:
            if self._discovered:
                return
            from pokequant.sources import adapters as _adapters_pkg
            for _, modname, _ in pkgutil.iter_modules(_adapters_pkg.__path__):
                try:
                    importlib.import_module(f"pokequant.sources.adapters.{modname}")
                except Exception as exc:
                    logger.warning("adapter discover failed for %s: %s", modname, exc)
            self._discovered = True

    def all_adapters(self) -> list[SourceAdapter]:
        return list(self._adapters)

    def get_adapter(self, name: str) -> SourceAdapter | None:
        for a in self._adapters:
            if a.name == name:
                return a
        return None

    def active_adapters(self, grade: Grade) -> list[SourceAdapter]:
        return [
            a for a in self._adapters
            if a.is_configured() and a.supports_grade(grade)
        ]

    def fetch_all(
        self, card_name: str, *, days: int, grade: Grade
    ) -> list[NormalizedSale]:
        """Parallel fan-out. Enforces NormalizedSale invariants on ingress.

        Emits one JSON line to stderr per adapter call.
        """
        self.discover()
        active = self.active_adapters(grade)
        if not active:
            return []

        results: list[NormalizedSale] = []
        fetched_at = time.time()

        with ThreadPoolExecutor(max_workers=max(1, len(active))) as pool:
            future_to_adapter = {
                pool.submit(self._fetch_one, a, card_name, days, grade): a
                for a in active
            }
            for fut in as_completed(future_to_adapter, timeout=_ADAPTER_TIMEOUT_S * 2):
                adapter = future_to_adapter[fut]
                t0 = time.time()
                try:
                    records = fut.result(timeout=_ADAPTER_TIMEOUT_S)
                except Exception as exc:
                    _emit_metric(
                        "adapter.fetch",
                        adapter=adapter.name,
                        card=card_name,
                        count=0,
                        latency_ms=round((time.time() - t0) * 1000, 1),
                        error=str(exc)[:200],
                    )
                    continue

                kept = 0
                for r in records:
                    try:
                        _validate(r)
                    except InvalidSaleRecord as exc:
                        logger.warning("drop invalid record: %s", exc)
                        continue
                    # Stamp fetched_at (adapter must not set it).
                    stamped_fields = {k: getattr(r, k) for k in r.__dataclass_fields__}
                    stamped_fields["fetched_at"] = fetched_at
                    results.append(NormalizedSale(**stamped_fields))
                    kept += 1
                _emit_metric(
                    "adapter.fetch",
                    adapter=adapter.name,
                    card=card_name,
                    count=kept,
                    latency_ms=round((time.time() - t0) * 1000, 1),
                    error=None,
                )

        return results

    def _fetch_one(
        self, adapter: SourceAdapter, card_name: str, days: int, grade: Grade
    ) -> Iterable[NormalizedSale]:
        return adapter.fetch(card_name, days=days, grade=grade)


# Module-level singleton.
registry = SourceRegistry()
