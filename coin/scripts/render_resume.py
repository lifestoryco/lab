#!/usr/bin/env python
"""Multi-variant resume orchestrator.

Per-locked-decision: every render call emits TWO or FOUR PDFs.

  - High-fit role (fit_score >= 80, OR explicit --variants 4): 4 PDFs
      {role:04d}_{archetype}.weasy.pdf            ← existing Ford/Jinja2 template
      {role:04d}_{archetype}.{primary_theme}.designed.pdf
      {role:04d}_{archetype}.{alt1_theme}.designed.pdf
      {role:04d}_{archetype}.{alt2_theme}.designed.pdf
      {role:04d}_{archetype}.engineeringresumes.ats.pdf
  - Normal role: 2 PDFs (weasy + ats only) OR 1 designed + 1 ats per
    flag.

After rendering, run the score panel on the ATS-strict variant and
persist a render_artifact row per output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH


def _load_generated_for_role(role_id: int) -> tuple[dict, Path]:
    generated_dir = ROOT / "data" / "resumes" / "generated"
    pattern = f"{role_id:04d}_*.json"
    matches = sorted(generated_dir.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No generated JSON found matching {pattern}")
    return json.loads(matches[-1].read_text()), matches[-1]


def render_multi_variant(
    generated_json: dict,
    *,
    role_id: int,
    output_dir: Path,
    high_fit: bool = False,
    explicit_variants: int | None = None,
    db_path: str | Path | None = None,
) -> list[dict]:
    """Render the full multi-variant set + persist render_artifact rows.

    Returns a list of {theme, variant_kind, pdf_path, ats_score, ...} dicts.
    """
    from careerops.rendercv_adapter import themes_for_lane
    from careerops import experience as exp

    archetype = generated_json.get("archetype_id") or "lane"
    themes = themes_for_lane(archetype)
    primary = themes["primary"]
    alts = themes.get("alts") or []

    n_variants = explicit_variants if explicit_variants is not None else (4 if high_fit else 2)
    artifacts: list[dict] = []

    if n_variants >= 1:
        # WeasyPrint variant via the existing render_pdf.py path. We import
        # render_pdf functions lazily because they pull WeasyPrint imports
        # which are slow to load.
        try:
            from scripts.render_pdf import render_pdf as legacy_render_pdf  # type: ignore
            weasy_path = output_dir / f"{role_id:04d}_{archetype}.weasy.pdf"
            legacy_render_pdf(generated_json, output_path=weasy_path)
            artifacts.append({
                "theme": "ford-jinja2",
                "variant_kind": "weasy",
                "pdf_path": str(weasy_path),
            })
        except Exception as e:
            # Don't fail the whole pipeline if WeasyPrint isn't wired for the
            # generated-json shape; log and continue. RenderCV is the primary.
            print(f"   ⚠ WeasyPrint variant skipped: {e}", file=sys.stderr)

    # RenderCV designed variant (primary theme).
    from scripts.render_rendercv import render_one
    if n_variants >= 2:
        pdf = render_one(
            generated_json,
            theme=primary,
            variant="designed",
            output_dir=output_dir,
            role_id=role_id,
        )
        artifacts.append({"theme": primary, "variant_kind": "designed", "pdf_path": str(pdf)})

    # RenderCV alt themes (only when n_variants == 4).
    if n_variants >= 4:
        for alt in alts[:2]:
            pdf = render_one(
                generated_json,
                theme=alt,
                variant="designed",
                output_dir=output_dir,
                role_id=role_id,
            )
            artifacts.append({"theme": alt, "variant_kind": "designed", "pdf_path": str(pdf)})

    # ATS-strict variant always emitted.
    pdf = render_one(
        generated_json,
        theme="engineeringresumes",
        variant="ats",
        output_dir=output_dir,
        role_id=role_id,
    )
    artifacts.append({"theme": "engineeringresumes", "variant_kind": "ats", "pdf_path": str(pdf)})

    # Score panel + persist.
    from careerops.score_panel import score_artifact
    persisted: list[dict] = []
    for art in artifacts:
        try:
            scored = score_artifact(
                pdf_path=Path(art["pdf_path"]),
                role_id=role_id,
                theme=art["theme"],
                variant_kind=art["variant_kind"],
                generated_json=generated_json,
                db_path=db_path,
            )
            persisted.append(scored)
        except Exception as e:
            print(f"   ⚠ Score panel failed for {art['pdf_path']}: {e}", file=sys.stderr)
            persisted.append(art)

    return persisted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("role_id", type=int, help="Role id to render")
    ap.add_argument("--variants", type=int, choices=[1, 2, 4], default=None,
                    help="Force variant count (default: 4 if fit>=80, else 2)")
    ap.add_argument("--output-dir", type=Path,
                    default=ROOT / "data" / "resumes" / "generated")
    args = ap.parse_args()

    gen, _src = _load_generated_for_role(args.role_id)
    fit = gen.get("fit_score") or 0
    high_fit = fit >= 80

    artifacts = render_multi_variant(
        gen,
        role_id=args.role_id,
        output_dir=args.output_dir,
        high_fit=high_fit,
        explicit_variants=args.variants,
    )

    print()
    print("─" * 60)
    print(f"  Render report — role {args.role_id}")
    print("─" * 60)
    for art in artifacts:
        scored = art.get("ats_score")
        keyword_pct = art.get("keyword_overlap_pct")
        density = art.get("buzzword_density_pct")
        truth = art.get("truthfulness_pass")
        page_count = art.get("page_count")
        line = (
            f"  [{art['variant_kind']:8s}] {art['theme']:22s} → "
            f"{Path(art['pdf_path']).name}"
        )
        if scored is not None:
            line += f"  | ATS={scored}  KW={keyword_pct or '-'}%  density={density or '-'}%  truth={'✅' if truth else '❌' if truth is not None else '-'}  pages={page_count or '-'}"
        print(line)
    print("─" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
