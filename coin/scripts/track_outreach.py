#!/usr/bin/env python
"""Update outreach.sent_at / outreach.replied_at after Sean sends or receives.

The outreach table tracks one row per drafted DM produced by /coin network-scan.
Sending happens manually (LinkedIn TOS — Coin never auto-sends), so Sean comes
back here to log the timestamps and keep the followup-cadence tracker accurate.

Usage:
  python scripts/track_outreach.py --id 12 sent
  python scripts/track_outreach.py --id 12 replied
  python scripts/track_outreach.py --id 12 sent --note "DM sent at 9am Tue"
  python scripts/track_outreach.py --list                  # show open drafts
  python scripts/track_outreach.py --list --role-id 4      # filter by role
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH


VALID_ACTIONS = ("sent", "replied")

# Static action → SQL map. Defence-in-depth: keeps column names out of f-strings
# even though VALID_ACTIONS already whitelists at the entry. If a future
# contributor adds a third action, the SQL must be added here too — review
# pressure stays loud.
_SQL_BY_ACTION: dict[str, dict[str, str]] = {
    "sent": {
        "no_note":   "UPDATE outreach SET sent_at = ? WHERE id = ?",
        "with_note": "UPDATE outreach SET sent_at = ?, notes = ? WHERE id = ?",
    },
    "replied": {
        "no_note":   "UPDATE outreach SET replied_at = ? WHERE id = ?",
        "with_note": "UPDATE outreach SET replied_at = ?, notes = ? WHERE id = ?",
    },
}


def _conn() -> sqlite3.Connection:
    # config.DB_PATH is always absolute (config._absolute_db_path() anchors
    # legacy relative defaults under the project root before export).
    db = Path(DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def update(outreach_id: int, action: str, note: str | None = None) -> dict:
    """Set sent_at or replied_at for an outreach row. Returns the updated row."""
    if action not in VALID_ACTIONS:
        raise ValueError(f"action must be one of {VALID_ACTIONS}; got {action!r}")
    sql_variant = _SQL_BY_ACTION[action]
    with _conn() as conn:
        if not _table_exists(conn, "outreach"):
            raise RuntimeError(
                "outreach table not present. Run "
                "scripts/migrations/m003_connections_outreach.py first."
            )
        existing = conn.execute(
            "SELECT id FROM outreach WHERE id = ?", (outreach_id,)
        ).fetchone()
        if not existing:
            raise ValueError(f"outreach id={outreach_id} not found")
        if note is None:
            conn.execute(sql_variant["no_note"], (_now(), outreach_id))
        else:
            conn.execute(sql_variant["with_note"], (_now(), note, outreach_id))
        row = conn.execute(
            "SELECT * FROM outreach WHERE id = ?", (outreach_id,)
        ).fetchone()
    return dict(row)


def list_open(role_id: int | None = None) -> list[dict]:
    """Return outreach rows with no sent_at (drafted but not sent)."""
    with _conn() as conn:
        if not _table_exists(conn, "outreach"):
            return []
        if role_id is not None:
            rows = conn.execute(
                """
                SELECT o.*, c.full_name AS contact_name, c.company AS contact_company
                FROM outreach o
                LEFT JOIN connections c ON c.id = o.connection_id
                WHERE o.sent_at IS NULL AND o.role_id = ?
                ORDER BY o.drafted_at DESC
                """,
                (role_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT o.*, c.full_name AS contact_name, c.company AS contact_company
                FROM outreach o
                LEFT JOIN connections c ON c.id = o.connection_id
                WHERE o.sent_at IS NULL
                ORDER BY o.drafted_at DESC
                """
            ).fetchall()
    return [dict(r) for r in rows]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, dest="outreach_id", help="outreach row id")
    ap.add_argument(
        "action",
        nargs="?",
        choices=VALID_ACTIONS,
        help="sent | replied — sets the corresponding timestamp to now()",
    )
    ap.add_argument("--note", help="optional note appended to outreach.notes")
    ap.add_argument(
        "--list",
        action="store_true",
        dest="list_mode",
        help="list outreach rows that have been drafted but not yet sent",
    )
    ap.add_argument(
        "--role-id",
        type=int,
        help="filter --list by role id",
    )
    args = ap.parse_args()

    if args.list_mode:
        rows = list_open(args.role_id)
        if not rows:
            print("No open outreach (everything drafted has been sent).")
            return 0
        print(f"Open outreach ({len(rows)} rows):")
        for r in rows:
            who = r.get("contact_name") or f"connection_id={r.get('connection_id')}"
            co = r.get("contact_company") or "—"
            print(
                f"  [#{r['id']}] role={r.get('role_id')}  "
                f"{who} @ {co}  warmth={r.get('warmth_score')}  "
                f"drafted_at={r.get('drafted_at')}"
            )
        return 0

    if not args.outreach_id or not args.action:
        ap.error("Provide --id <n> and an action (sent|replied), or --list.")

    try:
        row = update(args.outreach_id, args.action, args.note)
    except (ValueError, RuntimeError) as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    ts = row["sent_at"] if args.action == "sent" else row["replied_at"]
    print(
        f"✅ outreach[{row['id']}].{args.action}_at = {ts}"
        + (f"  (note: {row['notes']})" if row.get("notes") else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
