#!/usr/bin/env python
"""Parse a PDF resume and seed the experience DB from it.

Uses the clean-room parser in careerops/parser.py to extract:
  - name / contact (display only — base.py PROFILE is canonical for Sean)
  - experience-section bullets → accomplishment rows (position_slug derived)
  - skills section → preview only (Lightcast tagging happens via /coin capture)

By default runs --dry-run: previews the rows it would write and exits.
Pass --apply to commit.

Use case 1: Sean drops in his most-recent PDF resume to refresh the DB.
Use case 2: Pull stories from an old long-form CV / brag doc that aren't
            yet in base.py.

The experience DB is the source of truth from now on; base.py is a seed
input only. After ingest, /coin capture fleshes out STAR fields per
accomplishment.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _slug_for_position(company: str | None, fallback: str) -> str:
    import re
    if not company:
        return fallback
    return re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_") or fallback


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path", type=Path)
    ap.add_argument("--apply", action="store_true",
                    help="Commit rows (default: dry-run preview)")
    ap.add_argument("--position-slug", default=None,
                    help="Force a position_slug for all extracted bullets "
                         "(use when ingesting a single role's history)")
    ap.add_argument("--db", help="Override DB path")
    args = ap.parse_args()

    if not args.pdf_path.exists():
        print(f"❌ PDF not found: {args.pdf_path}", file=sys.stderr)
        return 1

    from careerops.parser import parse_resume_pdf
    from careerops import experience as exp

    print(f"Parsing {args.pdf_path}...")
    parse = parse_resume_pdf(args.pdf_path)
    print(f"  ATS-readiness: {parse.ats_score()}/100  pages={parse.n_pages}  lines={len(parse.lines)}")
    print(f"  Sections: {[s.canonical for s in parse.sections]}")
    print()
    print("Extracted contact fields:")
    for k, v in parse.fields.items():
        print(f"  {k}: {v.value!r}  (conf={v.confidence:.2f})")
    print()

    # Find experience section + extract bullet candidates.
    exp_section = next(
        (s for s in parse.sections if s.canonical == "experience"),
        None,
    )
    if not exp_section:
        print("⚠ No 'experience' section detected — nothing to seed.")
        return 0

    bullet_candidates: list[str] = []
    for ln in exp_section.lines:
        # Heuristic: bullets typically start with action verbs and are
        # 40-300 chars long. Headers (job titles) are shorter.
        text = ln.text.strip()
        if 30 < len(text) < 400 and text[0].isupper():
            bullet_candidates.append(text)

    print(f"Bullet candidates found: {len(bullet_candidates)}")
    if not bullet_candidates:
        print("  No qualifying bullets in experience section.")
        return 0

    pos_slug = args.position_slug or "ingested"
    print()
    if args.apply:
        n = 0
        for bt in bullet_candidates:
            exp.upsert_accomplishment(
                position_slug=pos_slug,
                title=bt[:60],
                raw_text_source=bt,
                db_path=args.db,
            )
            n += 1
        print(f"✅ Wrote {n} accomplishment rows under position_slug='{pos_slug}'")
        print("   Run /coin capture to flesh out STAR fields + tag skills.")
    else:
        print(f"[DRY-RUN] Would write {len(bullet_candidates)} accomplishments under "
              f"position_slug='{pos_slug}':")
        for bt in bullet_candidates[:8]:
            print(f"  - {bt[:90]}{'...' if len(bt) > 90 else ''}")
        if len(bullet_candidates) > 8:
            print(f"  ... and {len(bullet_candidates) - 8} more")
        print("   Re-run with --apply to commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
