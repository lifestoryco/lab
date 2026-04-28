"""Compensation utilities — parse, filter, and verify salary bands."""

import re
from config import MIN_BASE_SALARY


def parse_comp_string(raw: str | None) -> tuple[int | None, int | None]:
    """Parse a raw comp string like '$180K–$240K' into (min, max) integers."""
    if not raw:
        return None, None

    raw = raw.replace(",", "").replace(" ", "")
    numbers = re.findall(r"\$?(\d+(?:\.\d+)?)[Kk]?", raw)
    parsed = []
    for n in numbers:
        val = float(n)
        if val < 1000:
            val *= 1000  # e.g. "180K" → 180000
        parsed.append(int(val))

    if len(parsed) >= 2:
        return min(parsed), max(parsed)
    if len(parsed) == 1:
        return parsed[0], None
    return None, None


def filter_by_comp(roles: list[dict], min_base: int = MIN_BASE_SALARY) -> list[dict]:
    """Keep roles where comp_min >= min_base, or comp is unverified (don't exclude unknowns).

    Source priority: roles that arrive with `comp_min`/`comp_source` already
    populated (board scrapers set these explicitly) keep their values. Roles
    with only a raw string (LinkedIn) get parsed in place.
    """
    result = []
    for role in roles:
        if role.get("comp_min") is None and role.get("comp_max") is None:
            comp_min, comp_max = parse_comp_string(role.get("comp_raw"))
            role["comp_min"] = comp_min
            role["comp_max"] = comp_max
            if not role.get("comp_source"):
                role["comp_source"] = "explicit" if comp_min else "unverified"

        comp_min = role.get("comp_min")
        if comp_min is None or comp_min >= min_base:
            result.append(role)

    return result


def comp_band_label(comp_min: int | None, comp_max: int | None) -> str:
    """Return a human-readable comp band string."""
    if comp_min and comp_max:
        return f"${comp_min // 1000}K–${comp_max // 1000}K"
    if comp_min:
        return f"${comp_min // 1000}K+"
    return "unverified"


def estimate_total_comp(base_min: int, base_max: int, rsu_annual_est: int = 0) -> dict:
    """Estimate total comp range including RSU."""
    return {
        "base_range": comp_band_label(base_min, base_max),
        "rsu_annual_est": rsu_annual_est,
        "tc_min": base_min + rsu_annual_est,
        "tc_max": base_max + rsu_annual_est,
        "tc_label": comp_band_label(base_min + rsu_annual_est, base_max + rsu_annual_est),
    }
