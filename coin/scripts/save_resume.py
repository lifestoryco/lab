#!/usr/bin/env python
"""Save a resume JSON output to disk and transition pipeline state.

Reads the resume JSON from --input (a file path) or from stdin, validates
required keys, writes it to data/resumes/generated/<role_id>_<lane>_<date>.json,
and flips the role's status to `resume_generated`.

Usage:
  python scripts/save_resume.py --role-id 42 --lane cox-style-tpm --input /tmp/r.json
  cat r.json | python scripts/save_resume.py --role-id 42 --lane cox-style-tpm
"""

from __future__ import annotations

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import GENERATED_RESUMES_DIR, LANES
from careerops.pipeline import get_role, update_status, init_db

REQUIRED_KEYS = {"executive_summary", "top_bullets", "skills_matched", "cover_letter_hook"}

def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--role-id", type=int, required=True)
    ap.add_argument("--lane", required=True, help=f"One of: {list(LANES)}")
    ap.add_argument("--input", help="Path to resume JSON file. Omit to read stdin.")
    args = ap.parse_args()

    if args.lane not in LANES:
        print(f"Unknown lane '{args.lane}'. Valid: {list(LANES)}", file=sys.stderr)
        return 2

    role = get_role(args.role_id)
    if not role:
        print(f"Role {args.role_id} not found", file=sys.stderr)
        return 1

    if args.input:
        raw = Path(args.input).read_text()
    else:
        raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Input is not valid JSON: {exc}", file=sys.stderr)
        return 2

    missing = REQUIRED_KEYS - set(data)
    if missing:
        print(f"Missing required keys: {sorted(missing)}", file=sys.stderr)
        return 2

    out_dir = Path(GENERATED_RESUMES_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = out_dir / f"{args.role_id:04d}_{args.lane}_{date_str}.json"

    # Preserve useful metadata alongside the resume body
    payload = {
        "role_id": args.role_id,
        "lane": args.lane,
        "company": role.get("company"),
        "title": role.get("title"),
        "url": role.get("url"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "resume": data,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    update_status(args.role_id, "resume_generated", note=f"wrote {out_path.name}")
    print(str(out_path))
    return 0

if __name__ == "__main__":
    sys.exit(main())
