"""Migration runner package.

Each migration module exposes a public `apply(db_path)` function that is
idempotent and tracks state in the `schema_migrations` table. `run_all()`
applies them in order — called from `careerops.pipeline.init_db()` so a
fresh DB lands on the latest schema with no manual setup step.

To add a migration:
  1. Drop a new file at `m###_<name>.py` exposing `apply(db_path)`.
  2. Append it to `MIGRATIONS` below in numeric order.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class _Migration(Protocol):
    MIGRATION_ID: str
    def apply(self, db_path: str | Path) -> object: ...


def _load_migrations() -> list:
    # Lazy import so the package itself is cheap to import; modules pull in
    # sqlite3 / config which is fine at runtime but unnecessary at import.
    from . import (
        m001_archetypes_5_to_4,
        m002_offers_table,
        m003_connections_outreach,
        m004_outreach_role_tag,
    )
    return [
        m001_archetypes_5_to_4,
        m002_offers_table,
        m003_connections_outreach,
        m004_outreach_role_tag,
    ]


def run_all(db_path: str | Path) -> list[str]:
    """Apply every migration to `db_path` in order. Each is idempotent so
    repeated calls are safe. Returns the list of MIGRATION_IDs touched
    (informational; idempotent skip-paths still appear here)."""
    applied: list[str] = []
    for module in _load_migrations():
        module.apply(db_path)
        applied.append(getattr(module, "MIGRATION_ID", module.__name__))
    return applied
