#!/usr/bin/env python
"""Export the experience DB to JSON Resume v1.0.0 format.

JSON Resume (https://jsonresume.org/schema) is the lingua franca for
resume data interchange. Coin uses a richer SQLite schema internally;
this script flattens that schema to JSON Resume v1 for portability.

Mapping:
  base.py PROFILE name/email/phone/location → basics
  position rows → work[]
  accomplishment.raw_text_source for each position → work[].highlights[]
  skill rows tagged on accomplishments → skills[] (deduplicated)
  education from base.py (still canonical) → education[]
  certifications from base.py → certificates[]

Output goes to stdout by default; --out writes to a file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _load_profile():
    sys.path.insert(0, str(ROOT / "data" / "resumes"))
    from base import PROFILE  # type: ignore
    return PROFILE


def build_json_resume(*, db_path: str | Path | None = None) -> dict:
    from careerops import experience as exp
    profile = _load_profile()

    # ── basics ──
    creds = profile.get("credentials") or []
    label = profile.get("title") or ""
    if creds:
        label = f"{label}, {', '.join(creds)}"
    basics = {
        "name": profile.get("name", ""),
        "label": label,
        "email": profile.get("email", ""),
        "phone": profile.get("phone", ""),
        "url": "",
        "summary": profile.get("default_summary", ""),
        "location": {
            "city": profile.get("city", "").split(",")[0].strip() if profile.get("city") else "",
            "region": (
                profile.get("city", "").split(",")[1].strip()
                if profile.get("city") and "," in profile.get("city", "")
                else ""
            ),
            "countryCode": "US",
            "address": profile.get("city", ""),
        },
        "profiles": [
            {
                "network": "LinkedIn",
                "username": (profile.get("linkedin") or "").split("/in/")[-1].rstrip("/"),
                "url": (
                    f"https://{profile['linkedin']}"
                    if profile.get("linkedin") and not profile["linkedin"].startswith("http")
                    else profile.get("linkedin", "")
                ),
            }
        ],
    }

    # ── work ── group accomplishments by position_slug.
    work: list[dict] = []
    accomplishments = exp.list_accomplishments(db_path=db_path)
    by_slug: dict[str, list] = {}
    for a in accomplishments:
        by_slug.setdefault(a["position_slug"], []).append(a)

    # Use base.py for name/title/location/dates; fall back to slug.
    pos_lookup = {p["id"]: p for p in profile.get("positions", [])}
    seen_slugs: set[str] = set()
    for p in profile.get("positions", []):
        slug = p["id"]
        seen_slugs.add(slug)
        bullets = by_slug.get(slug, [])
        work.append({
            "name": p.get("company", ""),
            "position": p.get("title", ""),
            "location": p.get("location", ""),
            "url": "",
            "startDate": p.get("start", ""),
            "endDate": p.get("end", ""),
            "summary": p.get("summary", ""),
            "highlights": [a["raw_text_source"] for a in bullets if a["raw_text_source"]],
        })
    # Any orphan slugs not in base.py (e.g. ingested from a PDF).
    for slug, accs in by_slug.items():
        if slug in seen_slugs:
            continue
        work.append({
            "name": slug,
            "position": "",
            "location": "",
            "url": "",
            "startDate": "",
            "endDate": "",
            "summary": "",
            "highlights": [a["raw_text_source"] for a in accs if a["raw_text_source"]],
        })

    # ── skills ── union of tagged skills (Lightcast subset).
    seen_skills: dict[str, dict] = {}
    for a in accomplishments:
        for s in exp.list_skills_for_accomplishment(a["id"], db_path=db_path):
            sd = dict(s)
            seen_skills.setdefault(sd["slug"], {
                "name": sd["name"],
                "level": "",
                "keywords": [],
            })
    skills = list(seen_skills.values())
    if not skills and profile.get("skills"):
        # Fall back to base.py flat skill list.
        skills = [{"name": k, "level": "", "keywords": []} for k in profile["skills"][:20]]

    # ── education / certificates ── from base.py (still canonical).
    education = [
        {
            "institution": e.get("institution", ""),
            "url": "",
            "area": e.get("field", ""),
            "studyType": e.get("degree", ""),
            "startDate": "",
            "endDate": e.get("graduated", ""),
            "score": "",
            "courses": [],
        }
        for e in profile.get("education", [])
    ]
    certificates = [
        {
            "name": c.get("name", ""),
            "date": "",
            "issuer": c.get("issuer", ""),
            "url": "",
        }
        for c in profile.get("certifications", [])
    ]

    return {
        "$schema": "https://raw.githubusercontent.com/jsonresume/resume-schema/v1.0.0/schema.json",
        "basics": basics,
        "work": work,
        "education": education,
        "skills": skills,
        "certificates": certificates,
        "meta": {
            "canonical": "https://github.com/jsonresume/resume-schema",
            "version": "v1.0.0",
            "lastModified": "",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, help="Write to file (default: stdout)")
    ap.add_argument("--db", help="Override DB path")
    args = ap.parse_args()

    payload = build_json_resume(db_path=args.db)
    text = json.dumps(payload, indent=2)
    if args.out:
        args.out.write_text(text + "\n")
        print(f"✅ Wrote JSON Resume to {args.out}", file=sys.stderr)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
