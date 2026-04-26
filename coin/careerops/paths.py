"""Path-safety helpers shared by every script that takes a user-supplied path.

Centralised so the same `--input` / `--out` / `--csv` traversal guard is applied
identically everywhere. Each script previously rolled its own (or skipped it) —
that pattern is consolidated here.
"""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Repo's `coin/` directory (parent of careerops/)."""
    return Path(__file__).resolve().parent.parent


def validate_under(p: Path | str, allowed_root: Path | str, label: str) -> Path:
    """Refuse paths outside `allowed_root`. Resolves symlinks.

    Used as a SystemExit-on-violation guard for any script accepting a user-
    supplied filesystem path — prevents `--input /etc/passwd` style abuse and
    `--out ../../.ssh/foo` style writes outside the project's data tree.
    """
    resolved = Path(p).resolve()
    allowed = Path(allowed_root).resolve()
    # `parent == allowed` handles new files inside allowed/.
    # `startswith allowed + sep` handles nested files.
    sep = "/" if not str(allowed).endswith("/") else ""
    if resolved == allowed:
        return resolved
    if str(resolved).startswith(str(allowed) + sep) or resolved.parent == allowed:
        return resolved
    print(
        f"refusing {label}: {resolved}\n"
        f"  must live under: {allowed}",
        file=sys.stderr,
    )
    raise SystemExit(2)
