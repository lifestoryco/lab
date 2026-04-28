"""Comp imputation from the curated Levels.fyi seed.

Reads data/levels_seed.yml once, caches the parse, and exposes
lookup + impute helpers for the scoring + pipeline layers.

The seed is the source of truth. Run `/coin levels-refresh` quarterly
to walk through stale entries (older than 90 days). The mode is a
human-in-the-loop refresh — Levels.fyi is not auto-scraped.
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path

import yaml

_SEED_CACHE: dict | None = None
_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "levels_seed.yml"

# Levels we walk through when the role-title-derived target isn't in the
# company's ladder. Each fallback step costs 0.1 confidence (floor 0.3).
_LEVEL_FALLBACK_ORDER = ["principal", "staff", "L6", "L5", "L4"]

# Trailing legal/corporate suffixes stripped before fuzzy match.
_SUFFIX_PATTERN = re.compile(
    r"(\s*,\s*inc\.?$|\s+inc\.?$|\s+llc\.?$|\s+ltd\.?$|\s+corp\.?$|\s+corporation$|\.io$)",
    re.IGNORECASE,
)


def _seed_path() -> Path:
    return _SEED_PATH


def load_levels_seed() -> dict:
    """Read and cache data/levels_seed.yml.

    Empty file → returns ``{'companies': {}}``. Subsequent calls return
    the cache. Use ``_reset_cache()`` from tests to reload.
    """
    global _SEED_CACHE
    if _SEED_CACHE is not None:
        return _SEED_CACHE
    path = _seed_path()
    if not path.exists():
        _SEED_CACHE = {"companies": {}}
        return _SEED_CACHE
    raw = path.read_text()
    if not raw.strip():
        _SEED_CACHE = {"companies": {}}
        return _SEED_CACHE
    parsed = yaml.safe_load(raw) or {}
    if "companies" not in parsed or not isinstance(parsed["companies"], dict):
        parsed["companies"] = {}
    _SEED_CACHE = parsed
    return _SEED_CACHE


def _reset_cache() -> None:
    """Test-only — invalidates the parse cache."""
    global _SEED_CACHE
    _SEED_CACHE = None


def _normalize(company: str) -> str:
    """Lowercase + strip trailing legal suffixes."""
    if not company:
        return ""
    s = company.strip().lower()
    while True:
        new = _SUFFIX_PATTERN.sub("", s).strip()
        if new == s:
            break
        s = new
    return s


def lookup_company(company: str) -> dict | None:
    """Fuzzy match against the seed's `companies` keys.

    Returns the company entry dict (with `levels`, `last_refreshed`,
    etc.) or None on miss / `unknown: true`.

    Match rules — in priority order:
      1. Exact case-insensitive key match.
      2. After stripping trailing ", Inc.", " LLC", " Corp", ".io", etc.,
         exact case-insensitive key match.
      3. One-direction substring: a SEED key appears as a token (or full
         word boundary) inside the input. Reverse direction is rejected
         (e.g. 'Hash' MUST NOT match 'HashiCorp'). Mirrors
         score_company_tier's matcher.
    """
    if not company:
        return None
    seed = load_levels_seed()
    companies = seed.get("companies") or {}
    if not companies:
        return None

    raw = company.strip()
    raw_l = raw.lower()
    norm = _normalize(raw)

    # 1: exact (case-insensitive)
    for key, entry in companies.items():
        if key.lower() == raw_l:
            return _resolve_entry(entry)

    # 2: after suffix strip
    for key, entry in companies.items():
        if _normalize(key) == norm:
            return _resolve_entry(entry)

    # 3: one-direction substring — seed-key appears as token inside input
    padded = f" {norm} "
    for key, entry in companies.items():
        kn = _normalize(key)
        if not kn:
            continue
        if kn == norm:
            return _resolve_entry(entry)
        if " " in kn and kn in norm:
            return _resolve_entry(entry)
        if f" {kn} " in padded or norm.startswith(f"{kn} ") or norm.endswith(f" {kn}"):
            return _resolve_entry(entry)
    return None


def _resolve_entry(entry: dict) -> dict | None:
    if entry.get("unknown"):
        return None
    if not entry.get("levels"):
        return None
    return entry


# ── Imputation ────────────────────────────────────────────────────────

def _pick_level_key(role_title: str | None) -> tuple[str | None, float]:
    """Return (preferred_level_key, base_confidence) from the title.

    Title-matched → 0.7. No title hint → (None, 0.5) and the caller
    picks the company's default level.
    """
    if not role_title:
        return None, 0.5
    t = role_title.lower()
    # Order matters: 'vice president' beats 'principal' beats 'staff' etc.
    if "vp" in t.split() or "vice president" in t:
        return "vp", 0.7
    if "director" in t:
        return "director", 0.7
    if "principal" in t:
        return "principal", 0.7
    if "staff" in t:
        return "staff", 0.7
    return None, 0.5


def _company_default_level(levels: dict) -> str | None:
    """Pick the canonical 'senior IC' default for a company.

    Prefer L5 (senior IC across most ladders) over `staff` so a generic
    'Senior X' title doesn't impute against a Staff package. If neither
    is present, fall back to the first level in the ladder.
    """
    for candidate in ("L5", "staff", "L4", "L6"):
        if candidate in levels:
            return candidate
    return next(iter(levels.keys()), None)


def _walk_down(levels: dict, target: str) -> tuple[str | None, int]:
    """If target isn't present, walk down the fallback order. Returns
    (key_used, fallback_steps). 0 steps = target hit directly."""
    if target in levels:
        return target, 0
    if target not in _LEVEL_FALLBACK_ORDER:
        # Unknown target — try the default order from highest to lowest.
        for i, candidate in enumerate(_LEVEL_FALLBACK_ORDER):
            if candidate in levels:
                return candidate, i + 1
        return None, 0
    start = _LEVEL_FALLBACK_ORDER.index(target)
    for i, candidate in enumerate(_LEVEL_FALLBACK_ORDER[start:]):
        if candidate in levels:
            return candidate, i
    return None, 0


def _round_thousand(n: float) -> int:
    return int(round(n / 1000.0) * 1000)


def impute_comp(company: str, role_title: str | None = None) -> dict | None:
    """Return an imputed comp band for ``company`` using the seed.

    Returns None if the company isn't in the seed, is marked
    ``unknown: true``, or the ladder has no usable level.

    The returned dict matches the role-row contract used by
    pipeline.upsert_role and the scoring layer:

      {
        'comp_min': int,            # base_p25 + (rsu_4yr_p50/4) + bonus_p50
        'comp_max': int,            # base_p75 + (rsu_4yr_p50/4) + bonus_p50
        'comp_source': 'imputed_levels',
        'level_matched': 'staff' | 'L5' | ...,
        'confidence': 0.3..0.7,
      }
    """
    entry = lookup_company(company)
    if entry is None:
        return None
    levels = entry.get("levels") or {}
    if not levels:
        return None

    target, base_conf = _pick_level_key(role_title)
    if target is None:
        target = _company_default_level(levels)
        if target is None:
            return None

    key_used, fallback_steps = _walk_down(levels, target)
    if key_used is None:
        return None

    band = levels[key_used]
    base_p25 = band.get("base_p25") or band.get("base_p50")
    base_p50 = band.get("base_p50") or base_p25
    base_p75 = band.get("base_p75") or base_p50
    rsu_4yr = band.get("rsu_4yr_p50") or 0
    bonus = band.get("bonus_p50") or 0

    if base_p25 is None or base_p75 is None:
        return None

    annual_rsu = rsu_4yr / 4.0
    comp_min = _round_thousand(base_p25 + annual_rsu + bonus)
    comp_max = _round_thousand(base_p75 + annual_rsu + bonus)

    confidence = max(0.3, base_conf - 0.1 * fallback_steps)

    return {
        "comp_min": comp_min,
        "comp_max": comp_max,
        "comp_source": "imputed_levels",
        "level_matched": key_used,
        "confidence": round(confidence, 2),
    }


# ── Staleness / refresh helpers ───────────────────────────────────────

def _parse_date(value) -> _dt.date | None:
    if isinstance(value, _dt.date) and not isinstance(value, _dt.datetime):
        return value
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return _dt.date.fromisoformat(value)
        except ValueError:
            print(f"[levels] malformed last_refreshed: {value!r}", file=sys.stderr)
            return None
    return None


def get_seed_age(company: str) -> int | None:
    """Days between ``last_refreshed`` and today.

    Returns None when the company isn't in the seed OR
    ``last_refreshed`` can't be parsed. Note: this is the SEED-LEVEL
    age — companies marked ``unknown: true`` still report an age, since
    the unknown-flag is itself a refreshable claim.
    """
    if not company:
        return None
    seed = load_levels_seed()
    companies = seed.get("companies") or {}
    # Use lookup_company-style matching but also accept unknown entries.
    raw_l = company.strip().lower()
    norm = _normalize(company)
    entry = None
    for key, candidate in companies.items():
        if key.lower() == raw_l or _normalize(key) == norm:
            entry = candidate
            break
    if entry is None:
        return None
    last = _parse_date(entry.get("last_refreshed"))
    if last is None:
        return None
    return (_dt.date.today() - last).days


def flag_stale(threshold_days: int = 90) -> list[str]:
    """Sorted list of company names whose seed is older than threshold."""
    seed = load_levels_seed()
    companies = seed.get("companies") or {}
    today = _dt.date.today()
    out: list[str] = []
    for name, entry in companies.items():
        last = _parse_date(entry.get("last_refreshed"))
        if last is None:
            continue
        if (today - last).days > threshold_days:
            out.append(name)
    return sorted(out)
