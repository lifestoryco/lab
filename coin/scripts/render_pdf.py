#!/usr/bin/env python
"""Render a generated resume JSON to a print-ready PDF.

Usage:
  python scripts/render_pdf.py --role-id 4
  python scripts/render_pdf.py --input data/resumes/generated/0004_cox-style-tpm_2026-04-25.json
  python scripts/render_pdf.py --role-id 4 --out /tmp/netflix_tpm.pdf
"""

from __future__ import annotations

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import argparse
import json
from pathlib import Path

import yaml
from jinja2 import Template
from weasyprint import HTML

from careerops.pipeline import init_db, get_role, list_roles
from careerops.score import score_grade
from config import (
    GENERATED_RESUMES_DIR, RESUME_TEMPLATE_PATH, PROFILE_YAML_PATH, LANES
)


def _find_resume_file(role_id: int) -> Path | None:
    """Return the most recent generated resume file for a role."""
    d = Path(GENERATED_RESUMES_DIR)
    if not d.exists():
        return None
    candidates = sorted(d.glob(f"{role_id:04d}_*.json"), reverse=True)
    return candidates[0] if candidates else None


def render(role_id: int, resume_path: Path, out_path: Path) -> None:
    role = get_role(role_id)
    if not role:
        raise ValueError(f"Role {role_id} not found in DB")

    resume = json.loads(resume_path.read_text())

    from data.resumes.base import PROFILE
    profile_yml = yaml.safe_load(Path(PROFILE_YAML_PATH).read_text())

    lane = role.get("lane") or ""
    lane_cfg = profile_yml.get("archetypes", {}).get(lane, {})
    lane_label = LANES.get(lane, {}).get("label", lane)
    grade = score_grade(role["fit_score"]) if role.get("fit_score") is not None else None

    template_src = Path(RESUME_TEMPLATE_PATH).read_text()
    html_content = Template(template_src).render(
        profile=PROFILE,
        role=role,
        resume=resume,
        lane=lane,
        lane_label=lane_label,
        grade=grade,
    )

    HTML(string=html_content, base_url=str(Path.cwd())).write_pdf(str(out_path))
    print(f"PDF written → {out_path}")


def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--role-id", type=int, help="Role ID (auto-finds latest resume file)")
    ap.add_argument("--input", help="Path to resume JSON (overrides --role-id file lookup)")
    ap.add_argument("--out", help="Output PDF path (default: same dir as input, .pdf extension)")
    args = ap.parse_args()

    if not args.role_id and not args.input:
        ap.error("Provide --role-id or --input")

    if args.input:
        resume_path = Path(args.input)
        # Infer role ID from filename pattern NNNN_lane_date.json
        try:
            role_id = int(resume_path.stem.split("_")[0])
        except (ValueError, IndexError):
            ap.error("Cannot infer role ID from filename; pass --role-id explicitly")
    else:
        resume_path = _find_resume_file(args.role_id)
        if not resume_path:
            print(f"No generated resume found for role {args.role_id}. Run tailor first.", file=sys.stderr)
            return 1
        role_id = args.role_id

    out_path = Path(args.out) if args.out else resume_path.with_suffix(".pdf")

    render(role_id, resume_path, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
