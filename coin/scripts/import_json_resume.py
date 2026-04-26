#!/usr/bin/env python
"""Import a JSON Resume v1.0.0 file into the experience DB.

Round-trip pair to scripts/export_json_resume.py. Use cases:
  - Recruiter sends Sean a JSON Resume export to align on what they have
    on file → ingest, diff against current state.
  - Sean uses a different tool (Reactive-Resume, jsonresume.org themes)
    and wants to bring his data back into coin.

Highlights in JSON Resume's work[].highlights[] become accomplishment
rows. Skills become accomplishment_skill tags (best-effort via slug
lookup).

By default runs --dry-run; pass --apply to commit.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")


def import_json_resume(
    payload: dict,
    *,
    apply: bool = False,
    db_path: str | Path | None = None,
) -> dict[str, int]:
    """Returns counts dict: positions_seen, accomplishments_added,
    skills_tagged, skipped_unknown_skills."""
    from careerops import experience as exp

    stats = {
        "positions_seen": 0,
        "accomplishments_added": 0,
        "skills_tagged": 0,
        "skipped_unknown_skills": 0,
    }

    # Position slugs come from work[].name.
    work = payload.get("work") or []
    for w in work:
        stats["positions_seen"] += 1
        slug = _slugify(w.get("name") or "imported")
        for hl in w.get("highlights") or []:
            if not hl or not hl.strip():
                continue
            if not apply:
                stats["accomplishments_added"] += 1
                continue
            exp.upsert_accomplishment(
                position_slug=slug,
                title=hl[:60],
                raw_text_source=hl,
                time_period_start=w.get("startDate") or None,
                time_period_end=w.get("endDate") or None,
                db_path=db_path,
            )
            stats["accomplishments_added"] += 1

    # Skills (best-effort by slug-match against the Lightcast subset).
    skills = payload.get("skills") or []
    if apply:
        # Tag each skill against EVERY accomplishment we just imported in
        # the same run. Imprecise but useful as a starting point — Sean
        # refines via /coin capture.
        all_accs = exp.list_accomplishments(db_path=db_path)
        for s in skills:
            name = s.get("name") or ""
            cand_slug = _slugify(name)
            row = exp.get_skill_by_slug(cand_slug, db_path=db_path)
            if not row:
                # Try search.
                cand = exp.search_skills(name, limit=1, db_path=db_path)
                if cand:
                    row = cand[0]
            if not row:
                stats["skipped_unknown_skills"] += 1
                continue
            for a in all_accs:
                exp.tag_skill(
                    accomplishment_id=a["id"],
                    skill_slug=row["slug"],
                    weight=5,
                    db_path=db_path,
                )
                stats["skills_tagged"] += 1
    else:
        # Dry-run: just count name-matches.
        for s in skills:
            name = s.get("name") or ""
            cand_slug = _slugify(name)
            row = exp.get_skill_by_slug(cand_slug, db_path=db_path)
            if row:
                stats["skills_tagged"] += 1
            else:
                cand = exp.search_skills(name, limit=1, db_path=db_path)
                if cand:
                    stats["skills_tagged"] += 1
                else:
                    stats["skipped_unknown_skills"] += 1

    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--in", dest="in_path", type=Path, help="JSON Resume file")
    src.add_argument("--stdin", action="store_true", help="Read JSON Resume from stdin")
    ap.add_argument("--apply", action="store_true", help="Commit (default: dry-run)")
    ap.add_argument("--db", help="Override DB path")
    args = ap.parse_args()

    if args.stdin:
        payload = json.load(sys.stdin)
    else:
        payload = json.loads(args.in_path.read_text())

    stats = import_json_resume(payload, apply=args.apply, db_path=args.db)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] Import stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if not args.apply:
        print("   Re-run with --apply to commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
