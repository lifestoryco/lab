"""Resume-bullet linter — buzzwords, density, metric/outcome truth-gate.

This is the structural truthfulness gate referenced by modes/audit.md
Check 10 (metric ↔ outcome) and Check 11 (buzzword density).

Three concerns, one module:

1. **kill_words / soft_kills / density_flags** — loaded from
   data/linter/buzzwords.json. Hard-fail on kill_words; warn on
   soft_kills unless the bullet has linter_override; threshold-fail on
   density_flags above 6% of total tokens.

2. **Metric ↔ outcome truth gate** — extract every numeric token from a
   generated bullet (currency, percent, multiple, count, time-delta).
   Each must map to a row in `outcome` for the linked accomplishment.
   The numeric normalizer handles equivalences:
       $27M ↔ $27 million ↔ 27,000,000 ↔ 27M
       40% ↔ 40 percent
       6 weeks ↔ six weeks
   Mismatch → render refuses.

3. **Density check** — buzzword density above the configured threshold
   (default 6.0% in buzzwords.json) triggers a fail.

Used by:
- careerops/score_panel.py (post-render report)
- modes/audit.md Check 10 (truth gate)
- modes/tailor.md Step 2.5 (post-rewrite verify)
- scripts/render_resume.py (pre-export gate)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


BUZZWORDS_PATH = ROOT / "data" / "linter" / "buzzwords.json"


# ── Buzzword corpus (loaded once, lazy) ─────────────────────────────────

_corpus_cache: dict | None = None


def _load_corpus() -> dict:
    global _corpus_cache
    if _corpus_cache is None:
        if not BUZZWORDS_PATH.exists():
            raise FileNotFoundError(f"Buzzword corpus missing: {BUZZWORDS_PATH}")
        _corpus_cache = json.loads(BUZZWORDS_PATH.read_text())
    return _corpus_cache


def reload_corpus() -> dict:
    """Force re-read (used by tests that swap in a fresh buzzwords.json)."""
    global _corpus_cache
    _corpus_cache = None
    return _load_corpus()


# ── Numeric normalizer + metric extractor ───────────────────────────────
#
# All numeric tokens that appear in a generated bullet must trace to an
# outcome row. The normalizer reduces equivalent forms to a canonical
# representation so the comparison is robust:
#     $27M, $27 million, $27,000,000  →  ('USD', 27000000.0)
#     40%, 40 percent                 →  ('pct', 40.0)
#     12 months, twelve months        →  ('months', 12.0)
#     4.2x                             →  ('x', 4.2)
#     187 countries                    →  ('countries', 187.0)
#
# Returns (unit, numeric_value). Numbers are always float for comparison.

_WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
}

_SUFFIX_MULT = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def _word_num(token: str) -> float | None:
    return _WORD_NUMS.get(token.lower())


def _parse_currency_amount(amount: str, suffix: str | None) -> float:
    """('27', 'M') → 27_000_000.0. Handles commas + decimals + + signs."""
    cleaned = amount.replace(",", "").replace("+", "")
    n = float(cleaned)
    s = (suffix or "").upper()
    return n * _SUFFIX_MULT.get(s, 1)


# Regex set — purposely conservative; false-positives are bad for the
# truth gate. We require explicit cues ($, %, x, named units).

_RE_CURRENCY_RANGE = re.compile(
    r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(M|B|K)?\s+(?:to|-|–|—)\s+\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(M|B|K)?",
    re.IGNORECASE,
)
_RE_CURRENCY = re.compile(
    # Negative lookahead so "$27 million" doesn't match as "$27" + (later)
    # the million-word regex re-counts the same span.
    r"\$\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)(M|B|K)?\b(?!\s+(?:million|billion|thousand)\b)",
    re.IGNORECASE,
)
_RE_MILLION_WORD = re.compile(
    r"\$?\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s+(million|billion|thousand)\b",
    re.IGNORECASE,
)
_RE_PERCENT = re.compile(
    r"\b(\d{1,3}(?:\.\d+)?)\s?(?:%|percent\b)",
    re.IGNORECASE,
)
_RE_MULTIPLE = re.compile(r"\b(\d+(?:\.\d+)?)\s?x\b", re.IGNORECASE)
_RE_COUNT_WITH_UNIT = re.compile(
    r"\b(\d{1,3}(?:,\d{3})*\+?)\s+(countries|pages|localizations|"
    r"deployments|sites|teams|engineers|customers|stakeholders|"
    r"continents|time zones|languages|regions|markets)\b",
    re.IGNORECASE,
)
_RE_TIME_DELTA_NUM = re.compile(
    r"\b(\d+)\s+(weeks?|months?|years?|days?)\b",
    re.IGNORECASE,
)
_RE_TIME_DELTA_WORD = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty)"
    r"\s+(weeks?|months?|years?|days?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MetricToken:
    """A numeric claim extracted from bullet text.

    `unit` is canonicalized: 'USD' | 'pct' | 'x' | <pluralized-unit-word>.
    `value` is float for comparison.
    `display` is the original surface form (used in error messages).
    """
    unit: str
    value: float
    display: str


def extract_metrics(text: str) -> list[MetricToken]:
    """Pull every numeric claim from a bullet."""
    found: list[MetricToken] = []
    seen: set[tuple[str, float]] = set()

    def _add(unit: str, value: float, display: str):
        key = (unit, round(value, 4))
        if key in seen:
            return
        seen.add(key)
        found.append(MetricToken(unit=unit, value=value, display=display))

    # Currency ranges — emit BOTH endpoints.
    for m in _RE_CURRENCY_RANGE.finditer(text):
        for amt, suf in ((m.group(1), m.group(2)), (m.group(3), m.group(4))):
            _add("USD", _parse_currency_amount(amt, suf), f"${amt}{(suf or '').upper()}")

    for m in _RE_CURRENCY.finditer(text):
        amt, suf = m.group(1), m.group(2)
        _add("USD", _parse_currency_amount(amt, suf), f"${amt}{(suf or '').upper()}")

    for m in _RE_MILLION_WORD.finditer(text):
        amt, word = m.group(1), m.group(2).lower()
        suffix = {"million": "M", "billion": "B", "thousand": "K"}[word]
        _add("USD", _parse_currency_amount(amt, suffix), f"${amt} {word}")

    for m in _RE_PERCENT.finditer(text):
        v = float(m.group(1))
        _add("pct", v, f"{m.group(0).strip()}")

    for m in _RE_MULTIPLE.finditer(text):
        v = float(m.group(1))
        _add("x", v, f"{m.group(1)}x")

    for m in _RE_COUNT_WITH_UNIT.finditer(text):
        amt_raw, unit = m.group(1), m.group(2).lower()
        # Normalize unit (singularize the obvious ones).
        unit_canon = unit.rstrip("s") if unit.endswith("s") and unit not in ("teams",) else unit
        # Stay simple — match against outcome rows that store the original
        # form as well (we'll match against either singular or plural in the
        # comparison step).
        v = float(amt_raw.replace(",", "").replace("+", ""))
        _add(unit, v, f"{amt_raw} {unit}")

    for m in _RE_TIME_DELTA_NUM.finditer(text):
        amt_raw, unit = m.group(1), m.group(2).lower()
        unit_canon = unit if unit.endswith("s") else f"{unit}s"
        _add(unit_canon, float(amt_raw), f"{amt_raw} {unit}")

    for m in _RE_TIME_DELTA_WORD.finditer(text):
        word, unit = m.group(1).lower(), m.group(2).lower()
        n = _word_num(word)
        if n is None:
            continue
        unit_canon = unit if unit.endswith("s") else f"{unit}s"
        _add(unit_canon, float(n), f"{word} {unit}")

    return found


def metric_matches_outcomes(metric: MetricToken, outcome_rows: Iterable[dict]) -> bool:
    """Does `metric` correspond to any outcome row?

    A metric matches an outcome iff:
      - same canonical unit (or compatible: 'months' ↔ 'time delta in months')
      - same numeric value (within 0.5% tolerance)

    `outcome_rows` is an iterable of dicts with keys:
        value_numeric, unit, value_text
    """
    for o in outcome_rows:
        o_unit = (o.get("unit") or "").lower()
        o_val = o.get("value_numeric")
        if o_val is None:
            # Try to parse from value_text.
            try:
                o_val = float(re.sub(r"[^\d.]", "", o.get("value_text") or ""))
            except (ValueError, TypeError):
                continue

        # Unit compatibility map.
        if not _units_compatible(metric.unit, o_unit):
            continue

        # Numeric equality within 0.5% (or exact when very small).
        denom = max(abs(metric.value), abs(o_val), 1.0)
        if abs(metric.value - o_val) / denom <= 0.005:
            return True

        # Special case: counts where the bullet uses "1,000+" but outcome
        # stores 1000 — the linter should still accept "1,000+" as a match
        # for any value 1000 <= x ≤ 1500 (loose ceiling).
        d_str = (metric.display or "").lower()
        if "+" in d_str and o_val >= metric.value and o_val <= metric.value * 1.5:
            return True

    return False


def _units_compatible(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    if a == b:
        return True
    # Currency aliases.
    currency_units = {"usd", "$", "dollar", "dollars"}
    if a in currency_units and b in currency_units:
        return True
    # Singular/plural for time/count units.
    if a.rstrip("s") == b.rstrip("s"):
        return True
    # Outcome rows' synthetic metric_name e.g. 'count of pages' uses 'pages'
    # in unit; compare strict singular/plural.
    return False


# ── Buzzword/kill-word detection ────────────────────────────────────────

def _word_match_any(text: str, vocab: list[str]) -> list[str]:
    """Return phrases from vocab that appear in text (case-insensitive,
    whole-phrase match — no partials)."""
    tl = text.lower()
    hits = []
    for phrase in vocab:
        # Word-boundary match: surrounding chars must be non-word.
        # For multi-word phrases regex still works since boundaries
        # apply at start/end.
        pat = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
        if re.search(pat, tl):
            hits.append(phrase)
    return hits


def detect_kill_words(text: str) -> list[str]:
    return _word_match_any(text, _load_corpus().get("kill_words", []))


def detect_soft_kills(text: str) -> list[str]:
    return _word_match_any(text, _load_corpus().get("soft_kills", []))


def density_flag_count(text: str) -> tuple[int, list[str]]:
    """Number of density-flag occurrences + the flagged phrases that hit."""
    vocab = _load_corpus().get("density_flags", [])
    tl = text.lower()
    n = 0
    hits: list[str] = []
    for phrase in vocab:
        pat = r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)"
        for _ in re.finditer(pat, tl):
            n += 1
            hits.append(phrase)
    return n, hits


def buzzword_density_pct(text: str) -> float:
    """Density-flag occurrences as a percentage of total word tokens."""
    tokens = re.findall(r"\b\w+\b", text)
    if not tokens:
        return 0.0
    n, _ = density_flag_count(text)
    return round(100.0 * n / len(tokens), 2)


# ── Composite check used by the truth-gate caller ───────────────────────

@dataclass
class LintResult:
    """Per-bullet lint result. Density is NOT checked here — see lint_resume."""
    passed: bool
    kill_word_hits: list[str] = field(default_factory=list)
    soft_kill_hits: list[str] = field(default_factory=list)
    unverified_metrics: list[MetricToken] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def reason(self) -> str:
        bits: list[str] = []
        if self.kill_word_hits:
            bits.append(f"kill-words: {', '.join(self.kill_word_hits)}")
        if self.unverified_metrics:
            bits.append(
                "unverified metrics: "
                + ", ".join(m.display for m in self.unverified_metrics)
            )
        return "; ".join(bits) or "ok"


@dataclass
class ResumeLintResult:
    """Resume-wide lint: aggregates per-bullet results + density check.

    Density is computed over the concatenation of all bullets so a single
    short bullet with 'Drove' doesn't trip the threshold; only stuffing
    *across* the resume does.
    """
    passed: bool
    bullet_results: list[LintResult] = field(default_factory=list)
    density_pct: float = 0.0
    density_threshold: float = 6.0
    density_hits: list[str] = field(default_factory=list)

    def n_bullets_failed(self) -> int:
        return sum(1 for r in self.bullet_results if not r.passed)

    def reason(self) -> str:
        bits: list[str] = []
        nf = self.n_bullets_failed()
        if nf:
            bits.append(f"{nf} bullet(s) failed individual lint")
        if self.density_pct > self.density_threshold:
            bits.append(f"density {self.density_pct}% > {self.density_threshold}%")
        return "; ".join(bits) or "ok"


def lint_bullet(
    text: str,
    *,
    outcome_rows: Iterable[dict] | None = None,
    linter_override: str | None = None,
) -> LintResult:
    """Run kill-word + soft-kill + metric/outcome checks against one bullet.

    Density check is intentionally NOT here — see lint_resume() for the
    cross-bullet aggregate. A single short bullet can't be 'too dense'
    because the threshold is calibrated to a 100-token window.

    Args:
        text: the rendered bullet.
        outcome_rows: outcome rows linked to the source accomplishment.
                      If None, metric-truth check is skipped.
        linter_override: per-bullet allowlist string (semicolon-delimited
                         soft_kills permitted to appear). Empty = no override.
    """
    kw_hits = detect_kill_words(text)
    sk_hits = detect_soft_kills(text)

    if linter_override:
        allowed = {s.strip().lower() for s in linter_override.split(";") if s.strip()}
        sk_hits = [s for s in sk_hits if s.lower() not in allowed]

    unverified: list[MetricToken] = []
    if outcome_rows is not None:
        outcome_list = list(outcome_rows)
        for metric in extract_metrics(text):
            if not metric_matches_outcomes(metric, outcome_list):
                unverified.append(metric)

    passed = not kw_hits and not unverified
    notes = []
    if sk_hits:
        notes.append(f"soft-kills present: {', '.join(sk_hits)}")

    return LintResult(
        passed=passed,
        kill_word_hits=kw_hits,
        soft_kill_hits=sk_hits,
        unverified_metrics=unverified,
        notes=notes,
    )


def lint_resume(
    bullets: list[str],
    *,
    outcome_rows_per_bullet: list[Iterable[dict] | None] | None = None,
    linter_overrides: list[str | None] | None = None,
) -> ResumeLintResult:
    """Aggregate lint across the whole resume.

    Density is computed on the joined corpus of all bullets — the
    'percent of strong-verb tokens across the resume' signal is what
    actually correlates with stuffing.
    """
    corpus = _load_corpus()
    thresholds = corpus.get("thresholds", {})
    density_threshold = float(thresholds.get("density_pct_max", 6.0))

    bullet_results: list[LintResult] = []
    for i, b in enumerate(bullets):
        if not b:
            continue
        outcomes = (
            outcome_rows_per_bullet[i]
            if outcome_rows_per_bullet and i < len(outcome_rows_per_bullet)
            else None
        )
        override = (
            linter_overrides[i]
            if linter_overrides and i < len(linter_overrides)
            else None
        )
        bullet_results.append(
            lint_bullet(b, outcome_rows=outcomes, linter_override=override)
        )

    joined = " ".join(b for b in bullets if b)
    density_pct = buzzword_density_pct(joined)
    _, density_hits = density_flag_count(joined)

    any_bullet_failed = any(not r.passed for r in bullet_results)
    density_failed = density_pct > density_threshold

    return ResumeLintResult(
        passed=not any_bullet_failed and not density_failed,
        bullet_results=bullet_results,
        density_pct=density_pct,
        density_threshold=density_threshold,
        density_hits=density_hits,
    )


# ── CLI helper ──────────────────────────────────────────────────────────

def main() -> int:
    """Run lint on a generated resume JSON file, given a role id.

    Usage: python -m careerops.linter <generated_json_path>
    """
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="Path to a generated resume JSON")
    ap.add_argument("--role-id", type=int, help="Role id to lookup outcomes for (default: skip metric check)")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"❌ File not found: {p}", file=sys.stderr)
        return 1

    data = json.loads(p.read_text())
    bullets: list[str] = []
    for b in data.get("top_bullets", []) or []:
        if isinstance(b, str):
            bullets.append(b)
        elif isinstance(b, dict):
            bullets.append(b.get("text", ""))
    for pos in data.get("positions", []) or []:
        bullets.extend(pos.get("bullets", []) or [])

    res = lint_resume(bullets)
    for i, br in enumerate(res.bullet_results, 1):
        marker = "✅" if br.passed else "❌"
        print(f"{marker} bullet {i}: {br.reason()}")
    print()
    marker = "✅" if res.passed else "❌"
    print(f"{marker} resume density: {res.density_pct}% (threshold {res.density_threshold}%)")
    if res.density_hits:
        from collections import Counter
        top = Counter(res.density_hits).most_common(5)
        print(f"   density hits (top 5): {top}")
    print(f"\nBullets: {len(bullets)} | Failed: {res.n_bullets_failed()}")
    return 0 if res.passed else 1


if __name__ == "__main__":
    sys.exit(main())
