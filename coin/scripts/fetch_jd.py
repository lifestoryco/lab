#!/usr/bin/env python
"""Fetch and store the full JD text for a role.

Usage:
  python scripts/fetch_jd.py --id 42
"""

from __future__ import annotations

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import sys

from careerops.scraper import fetch_jd
from careerops.pipeline import get_role, update_jd_raw, init_db

def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--print", action="store_true", help="Also print JD to stdout")
    args = ap.parse_args()

    role = get_role(args.id)
    if not role:
        print(f"Role {args.id} not found", file=sys.stderr)
        return 1

    jd = fetch_jd(role["url"])
    if not jd:
        print(f"Could not fetch JD for role {args.id}", file=sys.stderr)
        return 2

    update_jd_raw(args.id, jd)
    print(f"stored {len(jd)} chars for role {args.id}")
    if args.print:
        print("---")
        print(jd)
    return 0

if __name__ == "__main__":
    sys.exit(main())
