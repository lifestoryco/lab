#!/usr/bin/env python
"""Render a generated cover-letter JSON to a print-ready PDF.

Usage:
  python scripts/render_cover_letter.py --role-id 4
  python scripts/render_cover_letter.py --input data/resumes/generated/0004_*_cover.json
  python scripts/render_cover_letter.py --role-id 4 --out /tmp/x_cover.pdf

Security parity with render_pdf.py:
  - Jinja2 environment uses autoescape (LLM-generated paragraphs cannot inject HTML).
  - WeasyPrint base_url is scoped to data/ so file:// references can only reach
    data/ assets — not .env, .git, or generated JSONs.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from pathlib import Path

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from config import (
    COVER_TEMPLATE_PATH,
    GENERATED_RESUMES_DIR,
    TEMPLATE_DIR,
)


def _find_cover_json(role_id: int) -> Path | None:
    d = Path(GENERATED_RESUMES_DIR)
    if not d.exists():
        return None
    candidates = sorted(d.glob(f"{role_id:04d}_*_cover.json"), reverse=True)
    return candidates[0] if candidates else None


def _build_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(enabled_extensions=("html",)),
    )


def render(cover_json_path: Path, out_path: Path) -> None:
    doc = json.loads(cover_json_path.read_text())
    required = {"company", "title", "today", "paragraphs"}
    missing = required - set(doc.keys())
    if missing:
        raise ValueError(f"Cover JSON missing keys: {sorted(missing)}")
    paragraphs = doc["paragraphs"]
    for k in ("hook", "proof", "fit"):
        if k not in paragraphs or not paragraphs[k]:
            raise ValueError(f"Cover JSON paragraphs.{k} is missing or empty")

    if not doc.get("audit_passes", False):
        raise ValueError(
            "Cover JSON has audit_passes != true — refusing to render. "
            "Re-run audit + fix before rendering."
        )

    from data.resumes.base import PROFILE

    env = _build_env()
    template = env.get_template(Path(COVER_TEMPLATE_PATH).name)
    html_content = template.render(
        profile=PROFILE,
        company=doc["company"],
        title=doc["title"],
        recipient_name=doc.get("recipient_name"),
        today=doc["today"],
        paragraphs=paragraphs,
    )

    base_url = str((Path.cwd() / TEMPLATE_DIR).resolve())
    HTML(string=html_content, base_url=base_url).write_pdf(str(out_path))
    print(f"Cover PDF written → {out_path}")


def _resolve_out_path(json_path: Path, override: str | None) -> Path:
    if override:
        return Path(override)
    return json_path.with_suffix(".pdf")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role-id", type=int)
    ap.add_argument("--input", help="Path to cover-letter JSON")
    ap.add_argument("--out", help="Output PDF path")
    args = ap.parse_args()

    if not args.role_id and not args.input:
        ap.error("Provide --role-id or --input")

    if args.input:
        json_path = Path(args.input)
    else:
        json_path = _find_cover_json(args.role_id)
        if not json_path:
            print(
                f"No cover-letter JSON for role {args.role_id}. "
                f"Run /coin cover-letter {args.role_id} first.",
                file=sys.stderr,
            )
            return 1

    out_path = _resolve_out_path(json_path, args.out)
    render(json_path, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
