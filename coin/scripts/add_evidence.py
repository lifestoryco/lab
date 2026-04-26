#!/usr/bin/env python
"""Upgrade evidence rows from `self_reported` → `manager_quoted | system_exported | public`.

Per locked decision #5: every base.py metric seeds with `source='self_reported'`
plus a notes field pointing back to the bullet. Sean uses this CLI as proof
surfaces (deck links, archived dashboards, manager testimonials, public
press releases) to upgrade the evidence chain over time.

Usage:
  # Show all evidence rows for an accomplishment
  python scripts/add_evidence.py 5 --list

  # Upgrade evidence by id with a URL
  python scripts/add_evidence.py 5 --evidence-id 1 --source public \
      --url https://example.com/cox-press-release \
      --notes "Cox press release announcing $1M Y1 revenue milestone"

  # Add a NEW evidence row to an existing outcome
  python scripts/add_evidence.py 5 --outcome-id 1 --source manager_quoted \
      --notes "Quote from VP Engineering email, Aug 2020"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops import experience as exp


def _list_evidence(acc_id: int) -> int:
    rows = exp.list_evidence(accomplishment_id=acc_id)
    if not rows:
        print(f"No evidence rows for accomplishment {acc_id}.")
        return 0
    print(f"Evidence for accomplishment {acc_id}:")
    for r in rows:
        rd = dict(r)
        print(
            f"  ev#{rd['id']}  outcome#{rd['outcome_id']}  source={rd['source']}  "
            f"kind={rd['kind']}  url={rd['url_or_path'] or '-'}"
        )
        if rd.get("notes"):
            print(f"     notes: {rd['notes']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("accomplishment_id", type=int)
    ap.add_argument("--list", action="store_true", help="List evidence rows for this accomplishment")
    ap.add_argument("--evidence-id", type=int, help="Upgrade an existing evidence row")
    ap.add_argument("--outcome-id", type=int, help="Add a new evidence row to this outcome")
    ap.add_argument("--source", choices=exp.VALID_EVIDENCE_SOURCES)
    ap.add_argument("--url", help="URL or file path")
    ap.add_argument("--notes")
    ap.add_argument("--kind", default="url", help="evidence kind: url|document|metric|reference")
    args = ap.parse_args()

    acc = exp.get_accomplishment(args.accomplishment_id)
    if not acc:
        print(f"❌ accomplishment {args.accomplishment_id} not found", file=sys.stderr)
        return 1

    if args.list:
        return _list_evidence(args.accomplishment_id)

    if args.evidence_id:
        if not args.source and not args.url and not args.notes:
            print("❌ --evidence-id requires at least one of --source/--url/--notes", file=sys.stderr)
            return 1
        exp.upgrade_evidence(
            args.evidence_id,
            source=args.source,
            url_or_path=args.url,
            notes=args.notes,
        )
        print(f"✅ Upgraded evidence row {args.evidence_id}")
        return 0

    if args.outcome_id:
        if not args.source:
            print("❌ --outcome-id requires --source", file=sys.stderr)
            return 1
        ev_id = exp.insert_evidence(
            outcome_id=args.outcome_id,
            kind=args.kind,
            source=args.source,
            url_or_path=args.url,
            notes=args.notes,
        )
        print(f"✅ Added evidence row {ev_id} to outcome {args.outcome_id}")
        return 0

    print("❌ Specify --list, --evidence-id, or --outcome-id", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
