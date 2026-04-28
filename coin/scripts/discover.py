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
import datetime
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
    ap.add_argument(
        "--max-age-days", type=int, default=None,
        help="Drop roles older than N days (by posted_at). Roles with unknown posted_at pass."
    )
    ap.add_argument(
        "--boards", type=str, default="linkedin,greenhouse,lever,ashby",
        help=(
            "CSV of sources to query. Default: linkedin,greenhouse,lever,ashby. "
            "Drop 'linkedin' to skip the LinkedIn pass; drop a board to skip it."
        ),
    )
    ap.add_argument(
        "--companies", type=str, default=None,
        help=(
            "CSV of company names from TARGET_COMPANIES to limit board scrapes to. "
            "Ignored for LinkedIn. Example: --companies 'Vercel,Datadog'."
        ),
    )
    args = ap.parse_args()

    boards_list = [b.strip() for b in (args.boards or "").split(",") if b.strip()]
    companies_list = (
        [c.strip() for c in args.companies.split(",") if c.strip()]
        if args.companies else None
    )

    if args.lane:
        # Single-lane: stitch LinkedIn + boards manually so the --boards flag still applies.
        scraped: list[dict] = []
        seen: set[str] = set()
        if "linkedin" in boards_list:
            try:
                for r in scraper.search(args.lane, limit=args.limit, location=args.location):
                    key = scraper._canonical_url(r.get("url"))
                    if key and key not in seen:
                        seen.add(key)
                        scraped.append(r)
            except Exception as exc:
                print(f"[linkedin] {args.lane} failed: {exc}", file=sys.stderr)
        board_subset = [b for b in ("greenhouse", "lever", "ashby") if b in boards_list]
        if board_subset:
            try:
                for r in scraper.search_boards(
                    args.lane,
                    location=args.location,
                    boards=board_subset,
                    companies=companies_list,
                ):
                    key = scraper._canonical_url(r.get("url"))
                    if key and key not in seen:
                        seen.add(key)
                        scraped.append(r)
            except Exception as exc:
                print(f"[boards] {args.lane} failed: {exc}", file=sys.stderr)
    else:
        scraped = scraper.search_all_lanes(
            limit_per_lane=args.limit,
            location=args.location,
            boards=boards_list,
            companies=companies_list,
        )

    if not args.skip_filter:
        scraped = compensation.filter_by_comp(scraped)

    if args.max_age_days is not None:
        cutoff = datetime.date.today() - datetime.timedelta(days=args.max_age_days)
        before = len(scraped)
        kept: list[dict] = []
        for r in scraped:
            pa = r.get("posted_at")
            if not pa:
                kept.append(r)
                continue
            try:
                if datetime.date.fromisoformat(pa) >= cutoff:
                    kept.append(r)
            except (ValueError, TypeError):
                kept.append(r)
        dropped = before - len(kept)
        print(
            f"--max-age-days {args.max_age_days}: dropped {dropped} of {before} "
            f"roles older than cutoff",
            file=sys.stderr,
        )
        scraped = kept

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
            "posted_at": role.get("posted_at"),
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
