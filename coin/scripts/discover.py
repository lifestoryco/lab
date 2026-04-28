#!/usr/bin/env python
"""Live discover + scoring pass. Pure Python — no LLM calls.

Stage 1 (always): scrape → cheap title/company score → store.
Stage 2 (optional, --deep-score N): for top-N by score_stage1, fetch the
full JD text and write data/.deep_score_pending.json so the host Claude
Code session can parse them via modes/discover.md Step 4a.

Per CLAUDE.md rule #6, the script never calls any LLM. JD parsing and
re-scoring run inside the host Claude Code session that executes discover.md.

Usage:
  python scripts/discover.py                              # all lanes, stage 1 only
  python scripts/discover.py --deep-score 15             # stage 1 + queue 15 for stage 2
  python scripts/discover.py --lane mid-market-tpm       # one lane
  python scripts/discover.py --limit 30 --location "San Francisco"
  python scripts/discover.py --deep-score 0              # explicitly disable stage 2
"""

from __future__ import annotations

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import datetime
import json
import uuid

import sys

from careerops import scraper, compensation, score
from careerops.pipeline import (
    init_db, upsert_role, update_fit_score, update_score_stage1,
    update_jd_raw, get_top_n_for_deep_score,
)

_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


def _run_deep_score_prep(
    n: int,
    lane: str | None,
    data_dir: pathlib.Path = _DATA_DIR,
) -> None:
    """Fetch JDs for top-N stage-1 roles and write the pending file.

    The pending file signals modes/discover.md Step 4a that JDs are ready
    for LLM parsing. The script itself makes no LLM calls.
    """
    candidates = get_top_n_for_deep_score(n=n, lane=lane)
    fetched = 0
    for role in candidates:
        try:
            jd_text = scraper.fetch_jd(role["url"])
            if jd_text:
                update_jd_raw(role["id"], jd_text)
                fetched += 1
        except Exception as exc:
            print(f"[fetch_jd] role {role.get('id')} failed: {exc}", file=sys.stderr)

    pending = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "discover_run_id": str(uuid.uuid4()),
        "role_ids": [r["id"] for r in candidates],
    }
    pending_file = data_dir / ".deep_score_pending.json"
    pending_file.write_text(json.dumps(pending, indent=2))
    count = len(candidates)
    print(
        f"### DEEP-SCORE-PENDING count={count} "
        f"file={pending_file}",
    )
    print(
        f"[deep-score] queued {count} roles ({fetched} JDs fetched). "
        f"Run /coin discover to parse via modes/discover.md Step 4a.",
        file=sys.stderr,
    )


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
    ap.add_argument(
        "--deep-score", type=int, default=15, metavar="N",
        help=(
            "After stage-1 scoring, fetch JDs and queue top-N for stage-2 LLM parse. "
            "Default: 15. Pass 0 to disable stage 2 entirely."
        ),
    )
    args = ap.parse_args()

    boards_list = [b.strip() for b in (args.boards or "").split(",") if b.strip()]
    companies_list = (
        [c.strip() for c in args.companies.split(",") if c.strip()]
        if args.companies else None
    )

    # ── Stage 1: scrape + title-score ────────────────────────────────────────

    if args.lane:
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
        update_score_stage1(role_id, fit)   # sets score_stage1 + fit_score + status
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

    # ── Stage 2 prep: queue top-N for JD parsing by host Claude session ──────

    if args.deep_score > 0:
        _run_deep_score_prep(args.deep_score, args.lane)

    return 0


def _tally(rows: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for r in rows:
        k = r.get(key) or "unknown"
        out[k] = out.get(k, 0) + 1
    return out


_DISCOVER_FAILED_FLAG = pathlib.Path(__file__).resolve().parent.parent / "data" / ".discover_failed.flag"


def _run_with_failure_flag() -> int:
    """Wrap main() so unhandled exceptions write a flag that notify.py reads."""
    import datetime as _dt
    try:
        # Clear stale flag at the start of every successful path through main().
        if _DISCOVER_FAILED_FLAG.exists():
            try:
                _DISCOVER_FAILED_FLAG.unlink()
            except OSError:
                pass
        return main()
    except Exception as exc:  # noqa: BLE001 — flag every unhandled error
        _DISCOVER_FAILED_FLAG.parent.mkdir(parents=True, exist_ok=True)
        _DISCOVER_FAILED_FLAG.write_text(
            f"{_dt.datetime.now().isoformat()}\n{type(exc).__name__}: {exc}\n"
        )
        raise


if __name__ == "__main__":
    sys.exit(_run_with_failure_flag())
