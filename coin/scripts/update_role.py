#!/usr/bin/env python
"""Update a role's status, fit score, or parsed JD.

Usage:
  python scripts/update_role.py --id 42 --status applied --note "submitted via greenhouse"
  python scripts/update_role.py --id 42 --fit 82.5
  python scripts/update_role.py --id 42 --parsed-jd /tmp/parsed.json
"""

from __future__ import annotations

import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import argparse
import json
from pathlib import Path

from careerops.pipeline import (
    init_db, update_status, update_fit_score, update_jd_parsed,
    STATUSES, TERMINAL_STATUSES,
)
from careerops.paths import validate_under

def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--status", choices=STATUSES)
    ap.add_argument("--note", help="Optional status-change note")
    ap.add_argument("--fit", type=float, help="Fit score 0-100")
    ap.add_argument("--parsed-jd", help="Path to JSON with parsed JD fields")
    args = ap.parse_args()

    if not any((args.status, args.fit is not None, args.parsed_jd)):
        print("Need at least one of --status, --fit, --parsed-jd", file=sys.stderr)
        return 2

    if args.status:
        update_status(args.id, args.status, note=args.note)
        if args.status in TERMINAL_STATUSES:
            print(f"role {args.id} → {args.status} (terminal)")
        else:
            print(f"role {args.id} → {args.status}")

    if args.fit is not None:
        update_fit_score(args.id, args.fit)
        print(f"role {args.id} fit={args.fit}")

    if args.parsed_jd:
        # --parsed-jd contents are persisted to roles.parsed_jd; constrain to data/
        # so callers cannot exfiltrate arbitrary file contents into the DB.
        validated = validate_under(Path(args.parsed_jd), ROOT / "data", "--parsed-jd")
        data = json.loads(validated.read_text())
        update_jd_parsed(args.id, data)
        print(f"role {args.id} parsed JD saved ({len(data)} keys)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
