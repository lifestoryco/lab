#!/usr/bin/env python
"""Render a generated cover-letter JSON to a print-ready PDF.

Usage:
  python scripts/render_cover_letter.py --role-id 4
  python scripts/render_cover_letter.py --input data/resumes/generated/0004_*_cover.json
  python scripts/render_cover_letter.py --role-id 4 --out data/resumes/generated/x_cover.pdf

Security parity with render_pdf.py:
  - Jinja2 environment uses autoescape (LLM-generated paragraphs cannot inject HTML).
  - WeasyPrint base_url is scoped to <project>/data/ so file:// references can
    only reach data/ assets — not .env, .git, or generated JSONs. base_url is
    pinned to the script's project root, NOT cwd, so the scope is stable
    regardless of where the caller invoked from.
  - --input and --out are constrained to data/resumes/generated/ — neither can
    read or write outside that directory.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Project root = repo/coin. Used for both sys.path and base_url anchoring.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import (  # noqa: E402  (sys.path mutated above)
    COVER_TEMPLATE_PATH,
    GENERATED_RESUMES_DIR,
    TEMPLATE_DIR,
)


def _find_cover_json(role_id: int) -> Path | None:
    d = ROOT / GENERATED_RESUMES_DIR
    if not d.exists():
        return None
    candidates = sorted(d.glob(f"{role_id:04d}_*_cover.json"), reverse=True)
    return candidates[0] if candidates else None


def _build_env():
    """Lazy import jinja2 so the no-op CLI path (e.g. role with no JSON) is fast."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    return Environment(
        loader=FileSystemLoader(str(ROOT / TEMPLATE_DIR)),
        autoescape=select_autoescape(enabled_extensions=("html",)),
    )


def _validate_under_generated(p: Path, label: str) -> Path:
    """Refuse paths outside data/resumes/generated/. Resolves symlinks."""
    resolved = p.resolve()
    allowed = (ROOT / GENERATED_RESUMES_DIR).resolve()
    # parent==allowed handles new files; startswith handles nested.
    if not str(resolved).startswith(str(allowed) + "/") and resolved.parent != allowed:
        raise ValueError(f"{label} must be under {allowed} (got {resolved})")
    return resolved


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
    from weasyprint import HTML

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

    # Anchor base_url to the project root, NOT cwd — invariant under shell cwd.
    base_url = str((ROOT / TEMPLATE_DIR).resolve())
    HTML(string=html_content, base_url=base_url).write_pdf(str(out_path))
    print(f"Cover PDF written → {out_path}")


def _resolve_out_path(json_path: Path, override: str | None) -> Path:
    if override:
        return _validate_under_generated(Path(override), "--out")
    return json_path.with_suffix(".pdf")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--role-id", type=int)
    ap.add_argument("--input", help="Path to cover-letter JSON (under data/resumes/generated/)")
    ap.add_argument("--out", help="Output PDF path (under data/resumes/generated/)")
    args = ap.parse_args()

    if not args.role_id and not args.input:
        ap.error("Provide --role-id or --input")

    if args.input:
        try:
            json_path = _validate_under_generated(Path(args.input), "--input")
        except ValueError as e:
            ap.error(str(e))
    else:
        json_path = _find_cover_json(args.role_id)
        if not json_path:
            print(
                f"No cover-letter JSON for role {args.role_id}. "
                f"Run /coin cover-letter {args.role_id} first.",
                file=sys.stderr,
            )
            return 1

    print(f"Selected cover JSON: {json_path}")
    out_path = _resolve_out_path(json_path, args.out)
    render(json_path, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
