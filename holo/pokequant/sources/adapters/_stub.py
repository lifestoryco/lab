"""Shared base for credential-gated adapter stubs.

Each concrete stub only needs to declare name + priority + credential
env var names. Defaults to disabled_by_default; health_check reports
which credential is missing so /api?action=health surfaces the setup gap.
"""
from __future__ import annotations

import os
from typing import Any, Sequence

from pokequant.sources.base import SourceAdapter
from pokequant.sources.schema import Grade, NormalizedSale


class CredentialStub(SourceAdapter):
    """Subclasses override name, priority, currency, required_env, stub_reason."""

    enabled_by_default = False
    required_env: tuple[str, ...] = ()
    stub_reason: str = "awaiting credentials"

    def supports_grade(self, grade: Grade) -> bool:
        return True

    def fetch(
        self, card_name: str, *, days: int, grade: Grade
    ) -> Sequence[NormalizedSale]:
        return []  # Stubs never fetch.

    def missing_credentials(self) -> list[str]:
        return [v for v in self.required_env if not os.environ.get(v)]

    def is_configured(self) -> bool:
        if not super().is_configured():
            return False
        return not self.missing_credentials()

    def health_check(self) -> dict[str, Any]:
        missing = self.missing_credentials()
        if missing:
            return {
                "ok": False,
                "latency_ms": 0.0,
                "error": f"{self.stub_reason}: missing {', '.join(missing)}",
            }
        return {
            "ok": False,
            "latency_ms": 0.0,
            "error": f"{self.stub_reason} (stub — fetch() returns empty)",
        }
