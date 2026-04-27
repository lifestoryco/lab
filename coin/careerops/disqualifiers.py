"""JD-aware disqualifier scanner.

Hard DQs quarantine the role to lane='out_of_band'. Soft DQs apply a
negative penalty to the composite score without quarantining. All rules
are deterministic regex — no LLM call. Coin runs inside the Claude Code
session; this layer is intentionally rule-based.

If you edit HARD_DQ_PATTERNS or SOFT_DQ_PATTERNS, mirror the same patterns
in `coin/config.py` (DISQUALIFIER_PATTERNS, DOMAIN_PENALTY_RULES) so the
config-editable surface stays in lockstep.
"""

from __future__ import annotations

import re
from typing import Callable, TypedDict


class DqResult(TypedDict):
    hard_dq: list[str]
    soft_dq: list[tuple[str, int]]
    matched_phrases: dict[str, str]


HARD_DQ_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(secret|top.secret|ts/sci|public trust)\s+clearance", re.I),
     "clearance_required"),
    (re.compile(r"\b(ITAR|22\s*CFR\s*120|22\s*CFR\s*121|export\s+controlled)\b", re.I),
     "itar_restricted"),
    (re.compile(
        r"(BS|Bachelor'?s?|MS|Master'?s?|B\.S\.|M\.S\.)\s+(degree\s+)?(in|of)\s+"
        r"(Computer Science|CS|Software Engineering|Electrical Engineering|"
        r"Mechanical Engineering|Materials Science|Chemical Engineering)\s+"
        r"(is\s+)?required",
        re.I,
     ), "degree_required"),
]


_MSFT_SKILLS = {"azure", ".net", "c#", "power bi", "d365",
                "dynamics 365", "power platform"}


def _msft_gate(jd: str, profile: dict) -> bool:
    skills = [s.lower() for s in profile.get("skills", [])]
    return not any(s in _MSFT_SKILLS for s in skills)


SOFT_DQ_PATTERNS: list[tuple[re.Pattern, str, int, Callable[[str, dict], bool]]] = [
    (re.compile(r"\b(Microsoft\s+stack|Azure|\.NET|C#|Power\s+Platform|"
                r"Power\s+BI|Dynamics\s+365|D365)", re.I),
     "msft_stack_mismatch", -20, _msft_gate),
    (re.compile(r"\b(cybersecurity|infosec|SIEM|SOC|threat\s+intel|penetration|"
                r"red\s+team|blue\s+team|zero\s+trust)\b", re.I),
     "narrow_security_domain", -20, lambda jd, p: True),
]


def scan_jd(jd_text: str, profile: dict) -> DqResult:
    result: DqResult = {"hard_dq": [], "soft_dq": [], "matched_phrases": {}}
    if not jd_text:
        return result

    for pattern, reason in HARD_DQ_PATTERNS:
        for m in pattern.finditer(jd_text):
            if reason == "degree_required":
                window = jd_text[m.end():m.end() + 30]
                if re.search(r"or equivalent", window, re.I):
                    continue
            if reason not in result["hard_dq"]:
                result["hard_dq"].append(reason)
                result["matched_phrases"][reason] = m.group(0)
            break

    for pattern, reason, penalty, gate in SOFT_DQ_PATTERNS:
        matches = pattern.findall(jd_text)
        if not matches:
            continue
        if reason == "narrow_security_domain":
            if len(matches) < 3:
                continue
            title = profile.get("_target_title", "") or ""
            if not re.search(r"\b(security|cyber)", title, re.I):
                continue
        if not gate(jd_text, profile):
            continue
        result["soft_dq"].append((reason, penalty))
        first = pattern.search(jd_text)
        if first:
            result["matched_phrases"][reason] = first.group(0)

    return result


def apply_disqualifiers(role: dict, parsed_jd: dict, profile: dict) -> DqResult:
    enriched = {**profile, "_target_title": role.get("title", "")}
    jd_text = role.get("jd_raw") or (parsed_jd or {}).get("raw", "") or ""
    dq = scan_jd(jd_text, enriched)
    if dq["hard_dq"]:
        role["lane"] = "out_of_band"
        existing = role.get("notes") or ""
        note = f"DQ: {','.join(dq['hard_dq'])}"
        role["notes"] = f"{existing}\n{note}".strip() if existing else note
    return dq
