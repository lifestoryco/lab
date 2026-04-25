#!/usr/bin/env python
"""Check whether open job postings are still live.

Marks roles 'closed' if the URL returns 404, redirects to a generic page, or
contains language indicating the posting was removed.

Usage:
  python scripts/liveness_check.py              # check + update DB
  python scripts/liveness_check.py --dry-run    # report only
  python scripts/liveness_check.py --id 4       # single role
"""

from __future__ import annotations

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import time

import httpx

from careerops.pipeline import init_db, get_role, list_roles, update_status, TERMINAL_STATUSES
from config import USER_AGENT, REQUEST_DELAY_SECONDS

DEAD_PHRASES = [
    "no longer accepting applications",
    "this job is closed",
    "position has been filled",
    "job listing is no longer available",
    "this position is no longer available",
    "job has expired",
    "this job posting has been removed",
]


def check_url(url: str) -> tuple[bool, str]:
    """Return (is_dead, reason). Network errors are NOT treated as dead."""
    try:
        r = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        if r.status_code == 404:
            return True, "HTTP 404"
        if r.status_code >= 400:
            return True, f"HTTP {r.status_code}"
        text = r.text.lower()
        for phrase in DEAD_PHRASES:
            if phrase in text:
                return True, f'"{phrase}"'
        return False, ""
    except httpx.TimeoutException:
        return False, "timeout (skipped)"
    except Exception as e:
        return False, f"error: {e}"


def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Report only — don't update DB")
    ap.add_argument("--id", type=int, help="Check a single role by ID")
    args = ap.parse_args()

    if args.id:
        role = get_role(args.id)
        roles = [role] if role else []
    else:
        roles = [r for r in list_roles(limit=200) if r["status"] not in TERMINAL_STATUSES]

    if not roles:
        print("No active roles to check.")
        return 0

    print(f"Checking {len(roles)} active role(s)...\n")

    closed_count = 0
    for role in roles:
        dead, reason = check_url(role["url"])
        tag = "DEAD" if dead else "live"
        flag = "✗" if dead else "✓"
        print(
            f"  [{flag}] #{role['id']:>3}  {(role['company'] or ''):<22} "
            f"{(role['title'] or '')[:40]:<40}  [{tag}] {reason}"
        )
        if dead and not args.dry_run:
            update_status(role["id"], "closed", note=f"liveness: {reason}")
            closed_count += 1
        if not dead:
            time.sleep(REQUEST_DELAY_SECONDS)

    suffix = " (dry run — no DB changes)" if args.dry_run else ""
    print(f"\n{closed_count} role(s) marked closed{suffix}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
