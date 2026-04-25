#!/usr/bin/env python
"""Render a generated resume JSON to a print-ready PDF.

Usage:
  python scripts/render_pdf.py --role-id 4
  python scripts/render_pdf.py --input data/resumes/generated/0004_mid-market-tpm_2026-04-25.json
  python scripts/render_pdf.py --role-id 4 --out /tmp/netflix_tpm.pdf
  python scripts/render_pdf.py --role-id 4 --recruiter

Security:
  - Jinja2 environment uses autoescape (LLM-generated bullets cannot inject HTML).
  - WeasyPrint base_url is scoped to data/ so file:// references can only reach
    data/ assets — not .env, .git, or generated JSONs containing raw JD text.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from pathlib import Path

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from careerops.pipeline import init_db, get_role
from careerops.score import score_grade
from config import (
    GENERATED_RESUMES_DIR,
    RESUME_TEMPLATE_PATH,
    RECRUITER_TEMPLATE_PATH,
    PROFILE_YAML_PATH,
    LANES,
    TEMPLATE_DIR,
)


def _find_resume_file(role_id: int) -> Path | None:
    """Return the most recent generated resume file for a role."""
    d = Path(GENERATED_RESUMES_DIR)
    if not d.exists():
        return None
    candidates = sorted(d.glob(f"{role_id:04d}_*.json"), reverse=True)
    return candidates[0] if candidates else None


def _build_env() -> Environment:
    """Jinja2 with autoescape on for HTML output. LLM bullets containing &, <,
    or </style> get escaped to entities — no layout breakage, no injection."""
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html",)),
    )


def render(role_id: int, resume_path: Path, out_path: Path, recruiter: bool = False) -> None:
    role = get_role(role_id)
    if not role:
        raise ValueError(f"Role {role_id} not found in DB")

    resume_doc = json.loads(resume_path.read_text())
    # JSON is wrapped: {role_id, lane, target_role, ..., resume: {executive_summary, top_bullets, ...}}
    if "resume" not in resume_doc:
        raise ValueError(
            f"{resume_path} is missing the 'resume' wrapper key. "
            f"Expected shape: {{role_id, lane, target_role, resume: {{...}}}}. "
            f"Re-tailor with: /coin tailor {role_id}"
        )
    resume = resume_doc["resume"]
    target_role = resume_doc.get("target_role")  # for header_role_for_pdf below

    from data.resumes.base import PROFILE, get_target_locations
    profile_yml = yaml.safe_load(Path(PROFILE_YAML_PATH).read_text())
    target_locations = get_target_locations()

    lane = role.get("lane") or ""
    lane_cfg = profile_yml.get("archetypes", {}).get(lane, {})
    lane_label = LANES.get(lane, {}).get("label", lane)
    grade = score_grade(role["fit_score"]) if role.get("fit_score") is not None else None

    # Recruiter PDF header role: use tailored target_role if present, else
    # the role's actual title, else PROFILE.title. This stops the SE/SA/RevOps
    # mismatch caught in the 2026-04-24 code review (audit Check 7).
    header_role = target_role or role.get("title") or PROFILE.get("title", "")

    template_name = (
        Path(RECRUITER_TEMPLATE_PATH).name if recruiter else Path(RESUME_TEMPLATE_PATH).name
    )
    env = _build_env()
    template = env.get_template(template_name)
    html_content = template.render(
        profile=PROFILE,
        role=role,
        resume=resume,
        lane=lane,
        lane_label=lane_label,
        grade=grade,
        header_role=header_role,
        target_role=target_role,
        target_locations=target_locations,
    )

    # base_url scoped to data/ — file:// resolution can only reach assets here,
    # not .env, .git, or other repo content.
    base_url = str((Path.cwd() / TEMPLATE_DIR).resolve())
    HTML(string=html_content, base_url=base_url).write_pdf(str(out_path))
    print(f"PDF written → {out_path}{' [recruiter mode]' if recruiter else ''}")


def _resolve_out_path(resume_path: Path, recruiter: bool, override: str | None) -> Path:
    if override:
        return Path(override)
    suffix = "_recruiter.pdf" if recruiter else ".pdf"
    return resume_path.parent / (resume_path.stem + suffix)


def main() -> int:
    init_db()
    ap = argparse.ArgumentParser()
    ap.add_argument("--role-id", type=int, help="Role ID (auto-finds latest resume file)")
    ap.add_argument("--input", help="Path to resume JSON (overrides --role-id file lookup)")
    ap.add_argument("--out", help="Output PDF path (default: same dir as input, .pdf extension)")
    ap.add_argument(
        "--recruiter",
        action="store_true",
        help="Render submission-ready resume (full work history, no targeting/fit/gap meta)",
    )
    args = ap.parse_args()

    if not args.role_id and not args.input:
        ap.error("Provide --role-id or --input")

    if args.input:
        resume_path = Path(args.input)
        try:
            role_id = int(resume_path.stem.split("_")[0])
        except (ValueError, IndexError):
            ap.error("Cannot infer role ID from filename; pass --role-id explicitly")
    else:
        resume_path = _find_resume_file(args.role_id)
        if not resume_path:
            print(
                f"No generated resume found for role {args.role_id}. Run tailor first.",
                file=sys.stderr,
            )
            return 1
        role_id = args.role_id

    out_path = _resolve_out_path(resume_path, args.recruiter, args.out)
    render(role_id, resume_path, out_path, recruiter=args.recruiter)
    return 0


if __name__ == "__main__":
    sys.exit(main())
