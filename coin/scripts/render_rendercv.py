#!/usr/bin/env python
"""Render a coin generated-resume JSON via RenderCV (Typst → PDF).

Single-theme mirror of scripts/render_pdf.py. Used standalone when you
want one specific theme; the multi-variant flow lives in render_resume.py.

Usage:
  python scripts/render_rendercv.py --json data/resumes/generated/0004_*.json --theme harvard
  python scripts/render_rendercv.py --role-id 4 --theme classic --variant ats
  python scripts/render_rendercv.py --role-id 4 --theme harvard
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH

VALID_VARIANTS = ("designed", "ats")


def render_one(
    generated_json: dict,
    *,
    theme: str,
    variant: str,
    output_dir: Path,
    role_id: int | None = None,
) -> Path:
    """Render one (theme, variant) PDF. Returns the PDF path."""
    if variant not in VALID_VARIANTS:
        raise ValueError(f"variant must be one of {VALID_VARIANTS}")

    from careerops.rendercv_adapter import coin_to_rendercv_model
    from rendercv.renderer.typst import generate_typst
    from rendercv.renderer.pdf_png import generate_pdf

    archetype = generated_json.get("archetype_id") or "lane"
    role_part = f"{role_id:04d}_" if role_id is not None else ""
    basename = f"{role_part}{archetype}.{theme}.{variant}"

    # ATS-strict variant excludes top_bullets and forces a single column
    # by relying on the engineeringresumes theme baseline (single-column,
    # plain glyphs, ASCII dashes per resume-eng research).
    include_top_bullets = (variant != "ats")
    include_summary = True
    actual_theme = "engineeringresumes" if variant == "ats" else theme

    model = coin_to_rendercv_model(
        generated_json,
        theme=actual_theme,
        output_dir=output_dir,
        output_basename=basename,
        include_summary=include_summary,
        include_top_bullets=include_top_bullets,
    )
    typst_path = generate_typst(model)
    pdf_path = generate_pdf(model, typst_path)
    if not pdf_path or not Path(pdf_path).exists():
        raise RuntimeError(
            f"RenderCV produced no PDF for theme={actual_theme} variant={variant}"
        )
    return Path(pdf_path)


def _load_generated_for_role(role_id: int) -> tuple[dict, Path]:
    """Find the most-recent generated JSON for role_id under data/resumes/generated/."""
    generated_dir = ROOT / "data" / "resumes" / "generated"
    pattern = f"{role_id:04d}_*.json"
    matches = sorted(generated_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No generated JSON found matching {pattern} in {generated_dir}")
    json_path = matches[-1]
    return json.loads(json_path.read_text()), json_path


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--json", type=Path, help="Path to generated resume JSON")
    src.add_argument("--role-id", type=int, help="Role id (loads latest generated JSON)")
    ap.add_argument("--theme", default="engineeringresumes",
                    help="RenderCV theme (classic, engineeringresumes, harvard, sb2nov, ...)")
    ap.add_argument("--variant", default="designed", choices=VALID_VARIANTS)
    ap.add_argument("--output-dir", type=Path, default=ROOT / "data" / "resumes" / "generated")
    args = ap.parse_args()

    if args.json:
        gen = json.loads(args.json.read_text())
        role_id = gen.get("role_id")
    else:
        gen, _src = _load_generated_for_role(args.role_id)
        role_id = args.role_id

    pdf_path = render_one(
        gen,
        theme=args.theme,
        variant=args.variant,
        output_dir=args.output_dir,
        role_id=role_id,
    )
    print(f"✅ Rendered: {pdf_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
