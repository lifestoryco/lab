#!/usr/bin/env python
"""Live discover + scoring pass. Pure Python — no LLM calls.

Scrapes all (or one) lane, filters by comp floor, computes heuristic fit
scores, and upserts into pipeline.db. Prints a JSON summary to stdout so
the calling Claude Code session can read it.

Usage:
  python scripts/discover.py                         # all lanes, default limits
  python scripts/discover.py --lane cox-style-tpm    # one lane
  python scripts/discover.py --limit 30 --location "San Francisco"
"""

from __future__ import annotations

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import json
import sys

from careerops import scraper, compensation, score
from careerops.pipeline import init_db, upsert_role, update_fit_score

def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", help="Limit discovery to one archetype")
    ap.add_argument("--limit", type=int, default=20, help="Max roles per lane")
    ap.add_argument("--location", help="Override default location")
    ap.add_argument("--skip-filter", action="store_true", help="Disable comp filter")
    args = ap.parse_args()

    if args.lane:
        scraped = scraper.search(args.lane, limit=args.limit, location=args.location)
    else:
        scraped = scraper.search_all_lanes(limit_per_lane=args.limit, location=args.location)

    if not args.skip_filter:
        scraped = compensation.filter_by_comp(scraped)

    saved = []
    for role in scraped:
        role_id = upsert_role(role)
        fit = score.score_fit(role, role.get("lane"))
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
