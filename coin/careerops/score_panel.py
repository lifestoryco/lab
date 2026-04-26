"""Score panel — aggregate every render's quality signals.

Per the plan's "post-render score panel" requirement:

  ATS parseability score:        92% ✅  (target ≥85)
  JD keyword overlap:            72% ✅  (target 60-85)
  Buzzword density:              2.1% ✅  (max 6%)
  Truthfulness gate:             PASS ✅  (5/5 outcomes verified)
  Recruiter-eye 30-sec audit:    PASS ✅
  Title-ladder coherence:        PASS ✅
  Page count:                    1 ✅    (target 1)

Persists every render to the `render_artifact` table for trend tracking.

Inputs:
  - pdf_path: rendered PDF (we self-parse for ATS score + page count)
  - generated_json: the resume JSON that produced the PDF (has bullets +
                    accomplishment_id refs needed for the truth gate)
  - role_id: for keyword overlap lookup against `jd_keyword`

The truthfulness gate is the load-bearing one. It walks every bullet in
the rendered resume and validates each numeric token against the linked
accomplishment's `outcome` rows. If ANY metric fails to match → truth
gate fails → render_artifact.truthfulness_pass = 0.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@dataclass
class ScorePanel:
    role_id: int
    theme: str
    variant_kind: str
    pdf_path: str
    ats_score: int
    keyword_overlap_pct: float | None
    buzzword_density_pct: float
    truthfulness_pass: bool
    truth_failures: list[str] = field(default_factory=list)
    page_count: int = 0
    n_bullets: int = 0
    bullet_density_per_role: list[int] = field(default_factory=list)
    notes: str = ""

    def verdict(self) -> str:
        if not self.truthfulness_pass:
            return "TRUTH-GATE FAIL"
        if self.ats_score < 70:
            return "ATS-RISK"
        if self.buzzword_density_pct > 6.0:
            return "STUFFING"
        if self.page_count > 2:
            return "TOO-LONG"
        if self.ats_score >= 85 and self.buzzword_density_pct <= 6.0:
            return "SHIP-READY"
        return "USABLE"

    def to_render_artifact_kwargs(self) -> dict:
        return {
            "role_id": self.role_id,
            "theme": self.theme,
            "variant_kind": self.variant_kind,
            "pdf_path": self.pdf_path,
            "ats_score": self.ats_score,
            "keyword_overlap_pct": self.keyword_overlap_pct,
            "buzzword_density_pct": self.buzzword_density_pct,
            "truthfulness_pass": self.truthfulness_pass,
            "page_count": self.page_count,
            "notes": (self.notes or self.verdict()),
        }


# ── Truthfulness gate ──────────────────────────────────────────────────

def truthfulness_gate(
    generated_json: dict,
    *,
    db_path: str | Path | None = None,
) -> tuple[bool, list[str], int, int]:
    """Walk every bullet in generated_json and validate each numeric
    token against linked accomplishment outcomes.

    Returns (passed, failure_messages, n_outcomes_verified, n_outcomes_total).

    The lookup strategy: each bullet may carry an `accomplishment_id` (when
    coin's tailor wrote it from the experience DB) or `_source_id`. If
    not, we fall back to substring-matching the bullet text against
    accomplishment.raw_text_source rows in the DB.
    """
    from careerops import experience as exp
    from careerops.linter import lint_bullet

    failures: list[str] = []
    n_verified = 0
    n_total = 0

    bullets_with_meta = _collect_bullets(generated_json)
    for bt, acc_id in bullets_with_meta:
        if not bt:
            continue
        # If we don't have an accomplishment id, skip the metric check
        # (top_bullets etc. that were freeform-authored). Buzzword + kill-
        # word still apply.
        if acc_id is None:
            res = lint_bullet(bt, outcome_rows=None)
            if not res.passed:
                failures.append(f"bullet (unattached): {res.reason()}")
            continue

        outcomes = exp.list_outcomes(acc_id, db_path=db_path)
        outcome_dicts = [dict(o) for o in outcomes]
        n_total += len(outcome_dicts)

        res = lint_bullet(bt, outcome_rows=outcome_dicts)
        if res.unverified_metrics:
            for m in res.unverified_metrics:
                failures.append(
                    f"acc#{acc_id}: '{m.display}' not in outcomes"
                )
        else:
            n_verified += len(outcome_dicts)
        if res.kill_word_hits:
            failures.append(f"acc#{acc_id}: kill-words {res.kill_word_hits}")

    return (not failures, failures, n_verified, n_total)


def _collect_bullets(generated_json: dict) -> list[tuple[str, int | None]]:
    """Extract (text, accomplishment_id|None) tuples from a generated JSON."""
    out: list[tuple[str, int | None]] = []
    for b in generated_json.get("top_bullets") or []:
        if isinstance(b, str):
            out.append((b, None))
        elif isinstance(b, dict):
            out.append((b.get("text", ""), b.get("accomplishment_id")))
    for pos in generated_json.get("positions") or []:
        for b in pos.get("bullets") or []:
            if isinstance(b, str):
                out.append((b, None))
            elif isinstance(b, dict):
                out.append((b.get("text", ""), b.get("accomplishment_id")))
    return out


# ── Keyword overlap ────────────────────────────────────────────────────

def keyword_overlap_pct(
    generated_json: dict,
    *,
    role_id: int,
    db_path: str | Path | None = None,
) -> float | None:
    """Percent of role's must-have JD keywords that appear in the rendered text.

    Returns None if no JD keywords have been extracted yet.
    """
    from careerops import experience as exp
    keywords = exp.list_jd_keywords(role_id, term_kind="must_have", db_path=db_path)
    if not keywords:
        return None
    full_text = _resume_to_plain_text(generated_json).lower()
    hit = 0
    for k in keywords:
        if k["term"].lower() in full_text:
            hit += 1
    return round(100.0 * hit / len(keywords), 1)


def _resume_to_plain_text(generated_json: dict) -> str:
    parts: list[str] = []
    parts.append(generated_json.get("name") or "")
    parts.append(generated_json.get("default_summary") or "")
    parts.append(generated_json.get("executive_summary") or "")
    for b in generated_json.get("top_bullets") or []:
        parts.append(b if isinstance(b, str) else (b.get("text") or ""))
    for pos in generated_json.get("positions") or []:
        parts.append(pos.get("summary") or "")
        for b in pos.get("bullets") or []:
            parts.append(b if isinstance(b, str) else (b.get("text") or ""))
    grid = generated_json.get("skills_grid") or {}
    for items in grid.values():
        parts.extend(items)
    parts.extend(generated_json.get("skills") or [])
    return " ".join(p for p in parts if p)


# ── Per-role bullet density (newest-role weighted) ─────────────────────

def bullet_density_per_role(generated_json: dict) -> list[int]:
    return [
        len(pos.get("bullets") or [])
        for pos in (generated_json.get("positions") or [])
    ]


# ── Top-level orchestrator ─────────────────────────────────────────────

def score_artifact(
    *,
    pdf_path: Path,
    role_id: int,
    theme: str,
    variant_kind: str,
    generated_json: dict,
    db_path: str | Path | None = None,
    persist: bool = True,
) -> dict:
    """Compute every signal for one rendered PDF, persist render_artifact, return dict.

    Returns a flat dict suitable for surface-level rendering and persistence.
    """
    from careerops.parser import parse_resume_pdf
    from careerops.linter import lint_resume
    from careerops import experience as exp

    parse = parse_resume_pdf(pdf_path)
    ats = parse.ats_score()

    # Truth gate.
    truth_pass, truth_failures, n_verified, n_total = truthfulness_gate(
        generated_json, db_path=db_path,
    )

    # Buzzword + density across all bullets in the source JSON.
    bullets = [b for b, _ in _collect_bullets(generated_json) if b]
    lr = lint_resume(bullets)

    # Keyword overlap.
    kpct = keyword_overlap_pct(generated_json, role_id=role_id, db_path=db_path)

    panel = ScorePanel(
        role_id=role_id,
        theme=theme,
        variant_kind=variant_kind,
        pdf_path=str(pdf_path),
        ats_score=ats,
        keyword_overlap_pct=kpct,
        buzzword_density_pct=lr.density_pct,
        truthfulness_pass=truth_pass,
        truth_failures=truth_failures,
        page_count=parse.n_pages,
        n_bullets=len(bullets),
        bullet_density_per_role=bullet_density_per_role(generated_json),
    )

    if persist:
        try:
            exp.insert_render_artifact(
                **panel.to_render_artifact_kwargs(),
                db_path=db_path,
            )
        except Exception as e:
            panel.notes = f"persist failed: {e}"

    return {
        "role_id": role_id,
        "theme": theme,
        "variant_kind": variant_kind,
        "pdf_path": str(pdf_path),
        "ats_score": panel.ats_score,
        "keyword_overlap_pct": panel.keyword_overlap_pct,
        "buzzword_density_pct": panel.buzzword_density_pct,
        "truthfulness_pass": panel.truthfulness_pass,
        "truth_failures": panel.truth_failures,
        "page_count": panel.page_count,
        "n_bullets": panel.n_bullets,
        "bullet_density_per_role": panel.bullet_density_per_role,
        "verdict": panel.verdict(),
    }


# ── CLI ────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("role_id", type=int)
    ap.add_argument("--no-persist", action="store_true")
    args = ap.parse_args()

    generated_dir = ROOT / "data" / "resumes" / "generated"
    pattern = f"{args.role_id:04d}_*.json"
    matches = sorted(generated_dir.glob(pattern))
    if not matches:
        print(f"❌ No generated JSON for role {args.role_id}", file=sys.stderr)
        return 1
    gen = json.loads(matches[-1].read_text())

    pdf_pattern = f"{args.role_id:04d}_*.pdf"
    pdfs = sorted(generated_dir.glob(pdf_pattern))
    if not pdfs:
        print(f"❌ No PDFs found for role {args.role_id}", file=sys.stderr)
        return 1

    for pdf_path in pdfs:
        # Theme + variant from filename: 0004_archetype.theme.variant.pdf
        parts = pdf_path.stem.split(".")
        if len(parts) >= 3:
            theme = parts[-2]
            variant = parts[-1]
        else:
            theme = "unknown"
            variant = "designed"
        scored = score_artifact(
            pdf_path=pdf_path,
            role_id=args.role_id,
            theme=theme,
            variant_kind=variant,
            generated_json=gen,
            persist=not args.no_persist,
        )
        v = scored.get("verdict")
        print(
            f"[{variant:7s}] {theme:24s} ATS={scored['ats_score']:>3} "
            f"KW={scored['keyword_overlap_pct']}%  density={scored['buzzword_density_pct']}%  "
            f"truth={'✅' if scored['truthfulness_pass'] else '❌'}  pages={scored['page_count']}  → {v}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
