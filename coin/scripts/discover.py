#!/usr/bin/env python
"""Live discover + scoring pass. Pure Python — no LLM calls.

Scrapes all (or one) lane, filters by comp floor, computes heuristic fit
scores, and upserts into pipeline.db. Prints a JSON summary to stdout so
the calling Claude Code session can read it.

Default scope: Utah + Remote, consultancies filtered. Override with
`--no-utah-remote` for an unrestricted scan.

Usage:
  python scripts/discover.py                         # all lanes, Utah+Remote
  python scripts/discover.py --lane mid-market-tpm   # one lane
  python scripts/discover.py --limit 30 --location "San Francisco"
  python scripts/discover.py --no-utah-remote        # unrestricted
"""

from __future__ import annotations

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import json

from careerops import scraper, compensation, score
from careerops.pipeline import init_db, upsert_role, update_fit_score
from data.resumes.base import PROFILE


# Consultancy / staff-aug exclusions. These shops style their roles like
# product-co TPM listings but Sean isn't trying to be a billable resource —
# they're a default-no per the search-defaults memory.
CONSULTANCY_BLOCKLIST = {
    "accenture", "deloitte", "kpmg", "ey", "ernst & young",
    "pwc", "pricewaterhousecoopers", "bcg", "boston consulting group",
    "mckinsey", "bain", "capgemini", "infosys", "tcs", "tata consultancy",
    "wipro", "cognizant", "ibm consulting", "ibm", "atos",
    "slalom", "north highland", "west monroe", "robert half",
    "insight global", "tek systems", "teksystems", "modis",
    "kforce", "randstad", "adecco", "manpower",
}

UTAH_KEYWORDS = ("utah", "salt lake", "draper", "lehi", "provo", "orem", "park city", "ut")


def _is_utah_or_remote(role: dict) -> bool:
    if int(role.get("remote") or 0):
        return True
    loc = (role.get("location") or "").lower()
    return any(kw in loc for kw in UTAH_KEYWORDS)


def _is_consultancy(role: dict) -> bool:
    co = (role.get("company") or "").lower().strip()
    if not co:
        return False
    return any(co == c or co.startswith(c + " ") or co.startswith(c + ",") for c in CONSULTANCY_BLOCKLIST)


def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", help="Limit discovery to one archetype")
    ap.add_argument("--limit", type=int, default=20, help="Max roles per lane")
    ap.add_argument("--location", help="Override default location")
    ap.add_argument("--skip-filter", action="store_true", help="Disable comp filter")
    ap.add_argument(
        "--utah-remote",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Constrain to Utah locations + remote roles, drop consultancies (default: on; --no-utah-remote disables)",
    )
    args = ap.parse_args()

    if args.lane:
        scraped = scraper.search(args.lane, limit=args.limit, location=args.location)
    else:
        scraped = scraper.search_all_lanes(limit_per_lane=args.limit, location=args.location)

    if not args.skip_filter:
        scraped = compensation.filter_by_comp(scraped)

    if args.utah_remote:
        scraped = [r for r in scraped if _is_utah_or_remote(r) and not _is_consultancy(r)]

    saved = []
    for role in scraped:
        role_id = upsert_role(role)
        # Pass PROFILE explicitly so score_breakdown skips the per-row reload.
        fit = score.score_fit(role, role.get("lane"), profile=PROFILE)
        update_fit_score(role_id, fit)
        saved.append({
            "id": role_id,
            "lane": role.get("lane"),
            "title": role.get("title"),
            "company": role.get("company"),
            "location": role.get("location"),
            "remote": role.get("remote"),
            "comp_min": role.get("comp_min"),
            "comp_max": role.get("comp_max"),
            "comp_source": role.get("comp_source"),
            "fit_score": fit,
            "source": role.get("source"),
            "url": role.get("url"),
        })

    saved.sort(key=lambda r: r.get("fit_score") or 0, reverse=True)
    print(json.dumps({
        "count": len(saved),
        "by_source": _tally(saved, "source"),
        "by_lane": _tally(saved, "lane"),
        "top": saved[:10],
    }, indent=2))
    return 0

def _tally(rows: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for r in rows:
        k = r.get(key) or "unknown"
        out[k] = out.get(k, 0) + 1
    return out

if __name__ == "__main__":
    sys.exit(main())
