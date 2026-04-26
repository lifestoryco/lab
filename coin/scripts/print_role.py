#!/usr/bin/env python
"""Print roles from the pipeline DB as JSON for the Claude Code session to read.

Usage:
  python scripts/print_role.py                      # list top active roles
  python scripts/print_role.py --id 42              # one role, full detail
  python scripts/print_role.py --status discovered  # filter by status
  python scripts/print_role.py --lane mid-market-tpm
  python scripts/print_role.py --top 3              # top-3 by fit_score
"""

from __future__ import annotations

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import json
import sys

from careerops.pipeline import get_role, list_roles, init_db

def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, help="Single role ID")
    ap.add_argument("--status", help="Filter by status")
    ap.add_argument("--lane", help="Filter by archetype")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--top", type=int, help="Return top-N by fit_score (overrides --limit)")
    ap.add_argument("--fields", help="Comma-separated field allowlist")
    args = ap.parse_args()

    if args.id:
        role = get_role(args.id)
        if not role:
            print(json.dumps({"error": f"role {args.id} not found"}))
            return 1
        print(json.dumps(_project(role, args.fields), indent=2))
        return 0

    limit = args.top if args.top else args.limit
    roles = list_roles(status=args.status, lane=args.lane, limit=limit)
    print(json.dumps([_project(r, args.fields) for r in roles], indent=2))
    return 0

def _project(role: dict, fields_csv: str | None) -> dict:
    # Strip heavy raw fields by default so Claude's context stays lean.
    if fields_csv:
        keep = [f.strip() for f in fields_csv.split(",") if f.strip()]
        return {k: role.get(k) for k in keep}
    out = dict(role)
    out.pop("jd_raw", None)  # keep jd_parsed but drop raw HTML
    return out

if __name__ == "__main__":
    sys.exit(main())
