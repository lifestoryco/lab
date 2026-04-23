"""Limitless TCG adapter — tournament meta-signal source.

play.limitlesstcg.com exposes a JSON API (no auth). Emits
source_type="meta_signal" records with price=0; extra carries
top8_count, event_count, deck_archetypes.

Consumed by a future /api?action=meta_signal endpoint (not wired in
this task — see H-1.10a follow-up).

Note: this adapter overlaps the roadmap item H-1.3 (tournament meta-
shift signal). Once H-1.3 gets a prompt, this adapter is the source
it consumes.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Sequence

from pokequant.http import session as _http_session
from pokequant.sources.base import SourceAdapter
from pokequant.sources.priority import priority_for
from pokequant.sources.schema import Grade, NormalizedSale

logger = logging.getLogger(__name__)

_BASE = "https://play.limitlesstcg.com/api"


class LimitlessAdapter(SourceAdapter):
    name = "limitless"
    enabled_by_default = False  # meta signals not yet consumed by any handler
    priority = priority_for("limitless")
    currency = "USD"

    def supports_grade(self, grade: Grade) -> bool:
        return grade == "raw"  # meta signals have no grade context

    def fetch(
        self, card_name: str, *, days: int, grade: Grade
    ) -> Sequence[NormalizedSale]:
        # Intentionally empty: the meta_signal endpoint is future work.
        # Flip enabled_by_default=True when /api?action=meta_signal lands.
        return []

    def health_check(self) -> dict[str, Any]:
        t0 = time.time()
        try:
            resp = _http_session().get(_BASE, timeout=5)
            latency = round((time.time() - t0) * 1000, 1)
            return {
                "ok": resp.status_code in (200, 301, 302, 404),  # base may 404
                "latency_ms": latency,
                "error": None,
            }
        except Exception as exc:
            return {
                "ok": False,
                "latency_ms": round((time.time() - t0) * 1000, 1),
                "error": str(exc)[:200],
            }


from pokequant.sources.registry import registry as _registry  # noqa: E402
_registry.register(LimitlessAdapter())
