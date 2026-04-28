"""Thin JSON CLI shim for Coin web dashboard mutations.

The Next.js web layer shells out to this module for any operation that
mutates pipeline state (status transitions, notes, tailor queuing). This
keeps all business logic — state-machine validation, comp math, tailoring —
in one Python source of truth.

Read paths (dashboard lists, role detail) go directly from Node via
better-sqlite3, not through here.

Usage:
  python -m careerops.web_cli track --id N --status STATUS [--note TEXT]
  python -m careerops.web_cli tailor --id N
  python -m careerops.web_cli notes  --id N --append TEXT

Exit codes: 0 = ok, 1 = user error (bad id / status), 2 = internal error.
Stdout: exactly one JSON line. Stderr: internal logging only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


def _ok(payload: dict) -> None:
    print(json.dumps({"ok": True, **payload}))


def _err(code: str, message: str, exit_code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": message, "code": code}))
    sys.exit(exit_code)


def _get_role_or_die(pip, role_id: int) -> dict:
    role = pip.get_role(role_id)
    if role is None:
        _err("ROLE_NOT_FOUND", f"role_id {role_id} not found")
    return role


# ── Subcommands ───────────────────────────────────────────────────────────────

def cmd_track(args: argparse.Namespace) -> None:
    from careerops import pipeline as pip

    role = _get_role_or_die(pip, args.id)
    previous_status = role.get("status")

    if args.status not in pip.STATUSES:
        _err("INVALID_STATUS", f"status {args.status!r} not valid; must be one of {pip.STATUSES}")

    pip.update_status(args.id, args.status)
    if args.note:
        pip.update_role_notes(args.id, args.note, append=True)

    _ok({
        "role_id": args.id,
        "status": args.status,
        "previous_status": previous_status,
    })


def cmd_tailor(args: argparse.Namespace) -> None:
    from careerops import pipeline as pip

    _get_role_or_die(pip, args.id)

    tailor_dir = _ROOT / "data" / "tailor_pending"
    tailor_dir.mkdir(parents=True, exist_ok=True)
    marker_file = tailor_dir / f"{args.id}.txt"

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    marker_file.write_text(f"{ts}\nqueued by web_cli\n")

    pip.update_role_notes(args.id, f"tailor requested via web at {ts}", append=True)

    _ok({
        "role_id": args.id,
        "queued": True,
        "note": f"Run /coin tailor {args.id} in next Claude session",
        "marker_file": str(marker_file),
    })


def cmd_notes(args: argparse.Namespace) -> None:
    from careerops import pipeline as pip

    _get_role_or_die(pip, args.id)

    if not args.append:
        _err("EMPTY_TEXT", "append text must not be empty")

    pip.update_role_notes(args.id, args.append, append=True)
    _ok({"role_id": args.id, "appended": len(args.append)})


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(prog="careerops.web_cli")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_track = sub.add_parser("track")
    p_track.add_argument("--id", type=int, required=True)
    p_track.add_argument("--status", required=True)
    p_track.add_argument("--note", default="")

    p_tailor = sub.add_parser("tailor")
    p_tailor.add_argument("--id", type=int, required=True)

    p_notes = sub.add_parser("notes")
    p_notes.add_argument("--id", type=int, required=True)
    p_notes.add_argument("--append", required=True)

    args = ap.parse_args()

    try:
        if args.cmd == "track":
            cmd_track(args)
        elif args.cmd == "tailor":
            cmd_tailor(args)
        elif args.cmd == "notes":
            cmd_notes(args)
    except SystemExit:
        raise
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "code": "INTERNAL_ERROR"}))
        sys.exit(2)


if __name__ == "__main__":
    main()
