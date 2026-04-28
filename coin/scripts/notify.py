#!/usr/bin/env python
"""COIN-SCHEDULER iMessage interrupt for fresh A-grade roles.

Selects roles discovered in the last N hours that hit the grade floor
and haven't been notified yet, and sends a single iMessage per role via
osascript → Messages.app. Idempotent: a row is updated to set
`notified_at` only after a successful osascript call.

Quiet by design — no roles, no message. A single failure flag from the
discover script (data/.discover_failed.flag) triggers a single
"discover failed" iMessage and short-circuits the role loop.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH  # noqa: E402

# Resolve DB path relative to repo root if not absolute (mirrors migrations).
_DB = Path(DB_PATH) if Path(DB_PATH).is_absolute() else (ROOT / DB_PATH)
_LOG_DIR = ROOT / "data" / "logs"
_DISCOVER_FAILED_FLAG = ROOT / "data" / ".discover_failed.flag"

NOTIFY_PHONE = os.environ.get("COIN_NOTIFY_PHONE", "").strip()


# ── grade ───────────────────────────────────────────────────────────────────

_GRADE_THRESHOLDS = [("A", 85.0), ("B", 70.0), ("C", 55.0), ("D", 40.0)]


def grade_from_score(score: float | None) -> str:
    if score is None:
        return "F"
    for letter, floor in _GRADE_THRESHOLDS:
        if score >= floor:
            return letter
    return "F"


def _grade_at_least(grade: str, minimum: str) -> bool:
    order = "FDCBA"
    return order.index(grade) >= order.index(minimum)


# ── helpers ─────────────────────────────────────────────────────────────────

def _humanize_age(discovered_at: object, now: _dt.datetime | None = None) -> str:
    """Render a humane age label like '3h ago' / '2d ago'.

    `discovered_at` is whatever the DB hands us — usually an ISO-8601 string
    with a UTC offset, but defensively we accept anything and degrade to '?'
    on parse failure (including non-string values from a buggy migration).
    """
    if not discovered_at or not isinstance(discovered_at, str):
        return "?"
    # discovered_at is stored UTC by pipeline.upsert_role; compare in UTC so
    # Sean (UTC-7) doesn't see ages that look 7h stale.
    now = now or _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    try:
        dt = _dt.datetime.fromisoformat(discovered_at.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    except (ValueError, AttributeError, TypeError):
        return "?"
    delta = now - dt
    seconds = int(delta.total_seconds())
    if seconds < 3600:
        return f"{max(seconds // 60, 1)}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _comp_label(role: dict) -> str:
    cmin = role.get("comp_min")
    cmax = role.get("comp_max")
    if not cmin and not cmax:
        return "comp unknown"

    def _k(n):
        return f"${int(n) // 1000}K"

    if cmin and cmax:
        return f"{_k(cmin)}–{_k(cmax)}"
    return _k(cmin or cmax)


def _applescript_escape(s: str) -> str:
    """Escape a string for safe inclusion in an AppleScript string literal.

    AppleScript strings use double quotes; \\ and " must be escaped. Newlines
    are not allowed inline — replace with literal \\n which AppleScript
    interprets as the line-feed sequence inside a double-quoted string.
    """
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _build_message(role: dict, now: _dt.datetime | None = None) -> str:
    score = role.get("fit_score") or 0
    grade = grade_from_score(score)
    lines = [
        "🎯 Coin: A-grade role",
        f"{role.get('company') or '?'} — {role.get('title') or '?'}",
        f"Lane: {role.get('lane') or '?'} · Fit {score:.0f} ({grade}) · {_comp_label(role)}",
        f"Posted {_humanize_age(role.get('discovered_at'), now)} · {role.get('location') or '?'}",
        role.get("url") or "",
    ]
    return "\n".join(lines)


def _send_imessage(message: str, phone: str, timeout: int = 15) -> tuple[int, str]:
    """Returns (returncode, stderr). Never raises on osascript failure.

    Both `message` and `phone` are escaped — phone today comes from
    `COIN_NOTIFY_PHONE` env (operator-controlled) but defense in depth costs
    nothing and protects against future code paths where phone might flow
    from a less-trusted source.
    """
    escaped = _applescript_escape(message)
    safe_phone = _applescript_escape(phone)
    script = (
        f'tell application "Messages" to send "{escaped}" '
        f'to buddy "{safe_phone}" of service "iMessage"'
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stderr or ""
    except subprocess.TimeoutExpired as e:
        return 124, f"osascript timed out after {timeout}s: {e}"
    except FileNotFoundError as e:
        return 127, f"osascript not found: {e}"


def _log_error(stderr: str) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    today = _dt.date.today().isoformat()
    path = _LOG_DIR / f"notify_{today}.error.log"
    with path.open("a") as f:
        f.write(f"[{_dt.datetime.now().isoformat()}] {stderr.rstrip()}\n")


# ── main ────────────────────────────────────────────────────────────────────

def _select_fresh_roles(
    conn: sqlite3.Connection, since_hours: int
) -> list[dict]:
    """Fresh, never-notified, non-terminal roles within the lookback window.

    Status filter intentionally excludes terminal states only — if Sean tracks
    a role into 'resume_generated' or 'applied' before notify runs, it should
    still trigger an interrupt the first time. Once notified_at is set the
    row is permanently filtered out.

    discovered_at is normalized via `replace('T',' ')` so the lexicographic
    comparison against `datetime('now', ?)` (which uses a space delimiter)
    works regardless of how the timestamp was stored.
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT *
          FROM roles
         WHERE replace(discovered_at, 'T', ' ') >= datetime('now', ?)
           AND status NOT IN ('offer','rejected','withdrawn','no_apply','closed')
           AND notified_at IS NULL
        """,
        (f"-{since_hours} hours",),
    ).fetchall()
    return [dict(r) for r in rows]


def _handle_discover_failed_flag(args, phone: str) -> bool:
    """Returns True if the flag short-circuited the run."""
    if not _DISCOVER_FAILED_FLAG.exists():
        return False
    msg = (
        "🚨 Coin discover failed today — check logs at "
        f"data/logs/discover_{_dt.date.today().isoformat()}.log"
    )
    if args.dry_run:
        print(msg)
        return True
    _send_imessage(msg, phone)
    try:
        _DISCOVER_FAILED_FLAG.unlink()
    except FileNotFoundError:
        pass
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Notify Sean about fresh top-grade roles.")
    ap.add_argument("--since-hours", type=int, default=24)
    ap.add_argument("--min-grade", choices=("A", "B", "C", "D"), default="A")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not NOTIFY_PHONE and not args.dry_run:
        print("COIN_NOTIFY_PHONE not set — skipping notify")
        return 0

    if _handle_discover_failed_flag(args, NOTIFY_PHONE):
        return 0

    if not _DB.exists():
        print(f"DB not found at {_DB} — nothing to notify")
        return 0

    conn = sqlite3.connect(_DB)
    try:
        roles = _select_fresh_roles(conn, args.since_hours)
        sent = 0
        for role in roles:
            grade = grade_from_score(role.get("fit_score"))
            if not _grade_at_least(grade, args.min_grade):
                continue
            message = _build_message(role)
            if args.dry_run:
                print(message)
                print("---")
                continue
            rc, stderr = _send_imessage(message, NOTIFY_PHONE)
            if rc != 0:
                _log_error(f"role {role['id']}: rc={rc} stderr={stderr}")
                continue
            conn.execute(
                "UPDATE roles SET notified_at = datetime('now') WHERE id = ?",
                (role["id"],),
            )
            conn.commit()
            sent += 1
        if not args.dry_run:
            print(f"Notify: sent={sent} (since-hours={args.since_hours}, min-grade={args.min_grade})")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
