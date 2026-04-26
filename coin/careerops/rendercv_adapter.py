"""Map a coin generated-resume JSON to a RenderCV Pydantic model.

Coin's resume JSON shape (legacy, from existing render_pdf.py path):
    {
      "archetype_id": "mid-market-tpm",
      "role_id": <int>,
      "executive_summary": "...",
      "top_bullets": [...],
      "name": "Sean Ivins", "credentials": [...], "title": "...",
      "city": "Salt Lake City, UT", "phone": "...", "email": "...",
      "linkedin": "linkedin.com/in/seanivins",
      "positions": [{ "company", "title", "location", "start", "end", "summary", "bullets" }],
      "skills_grid": { "Program Management": [...], ... },
      "education": [...],
      "certifications": [...]
    }

RenderCV's data model is:
    cv:
      name, location, email, phone, website
      social_networks: [{ network, username }]
      sections: { <Section Title>: [<Entry|str>, ...] }
    design:
      theme

Entries can be:
    - bare string (interpreted as a TextEntry)
    - ExperienceEntry: { company, position, start_date, end_date, location, highlights }
    - EducationEntry: { institution, area, degree, start_date, end_date, location, highlights }

We emit:
    - "Summary": [executive_summary string]
    - "Selected Achievements": [top_bullets as strings, optional]
    - "Experience": ExperienceEntry per coin position
    - "Skills": one TextEntry per skills_grid category, formatted as "Category: a, b, c"
    - "Education": EducationEntry per coin education row
    - "Certifications": TextEntry per cert
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── Date normalization ──────────────────────────────────────────────────

_MONTHS = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09", "sept": "09",
    "oct": "10", "nov": "11", "dec": "12",
}


def _normalize_phone(phone: str | None) -> str | None:
    """RenderCV uses phonenumbers and validates E.164. Normalize US numbers
    formatted as 801.803.3084 / (801) 803-3084 / 801-803-3084 → +1 801 803 3084."""
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if len(digits) == 10:
        return f"+1 {digits[0:3]} {digits[3:6]} {digits[6:]}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+1 {digits[1:4]} {digits[4:7]} {digits[7:]}"
    # Fall back: prepend + if not already, hope it parses.
    if phone.strip().startswith("+"):
        return phone.strip()
    return f"+{digits}"


def _to_iso_month(date_str: str | None) -> str | None:
    """Normalize 'Jan 2025', 'Present', 'Apr 2013' → '2025-01' / 'present' / '2013-04'.

    RenderCV accepts ISO-style YYYY or YYYY-MM, plus 'present'.
    """
    if not date_str:
        return None
    s = date_str.strip().lower()
    if s in ("present", "current", "now"):
        return "present"
    m = re.match(r"^([a-z]+)\s+(\d{4})$", s)
    if m:
        month = _MONTHS.get(m.group(1)[:4])
        if month:
            return f"{m.group(2)}-{month}"
    m = re.match(r"^(\d{4})$", s)
    if m:
        return s
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        return s
    return None


# ── Coin → RenderCV YAML-dict adapter ───────────────────────────────────

def _socials_from_coin(linkedin: str | None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if linkedin:
        # Pull username from "linkedin.com/in/<slug>" or full URL.
        m = re.search(r"linkedin\.com/in/([\w\-_.]+)", linkedin, re.IGNORECASE)
        if m:
            out.append({"network": "LinkedIn", "username": m.group(1)})
    return out


def _experience_entry(position: dict) -> dict:
    """Coin position → RenderCV ExperienceEntry dict."""
    bullets: list[str] = list(position.get("bullets") or [])
    return {
        "company": position.get("company", ""),
        "position": position.get("title", ""),
        "start_date": _to_iso_month(position.get("start")),
        "end_date": _to_iso_month(position.get("end")),
        "location": position.get("location"),
        "highlights": bullets,
    }


def _education_entry(edu: dict) -> dict:
    """Coin education → RenderCV EducationEntry dict."""
    # Coin: { degree, field, institution, graduated }
    graduated = _to_iso_month(edu.get("graduated"))
    return {
        "institution": edu.get("institution", ""),
        "area": edu.get("field", ""),
        "degree": edu.get("degree", ""),
        "start_date": None,
        "end_date": graduated,
        "highlights": [],
    }


def _skills_section(skills_grid: dict[str, list[str]] | None) -> list[str]:
    """Format skills_grid as a list of 'Category: a, b, c' strings."""
    if not skills_grid:
        return []
    return [
        f"**{cat}:** " + ", ".join(items)
        for cat, items in skills_grid.items()
    ]


def _certs_section(certs: list[dict] | None) -> list[str]:
    if not certs:
        return []
    out: list[str] = []
    for c in certs:
        line = c.get("name", "")
        issuer = c.get("issuer")
        if issuer:
            line += f" — {issuer}"
        valid = c.get("valid")
        if valid:
            line += f" *(valid {valid})*"
        out.append(line)
    return out


def coin_to_rendercv_dict(
    generated_json: dict,
    *,
    theme: str,
    include_summary: bool = True,
    include_top_bullets: bool = True,
) -> dict:
    """Build a RenderCV-compatible YAML-style dict from coin's resume JSON."""
    name = generated_json.get("name", "")
    creds = generated_json.get("credentials") or []
    if creds:
        name = f"{name}, {', '.join(creds)}"
    cv_dict: dict[str, Any] = {
        "name": name,
        "location": generated_json.get("city"),
        "email": generated_json.get("email"),
        "phone": _normalize_phone(generated_json.get("phone")),
        "website": None,
        "social_networks": _socials_from_coin(generated_json.get("linkedin")),
        "sections": {},
    }

    sections = cv_dict["sections"]

    # Summary section.
    if include_summary:
        summary = generated_json.get("executive_summary") or generated_json.get("default_summary")
        if summary:
            sections["Summary"] = [summary.strip()]

    # Selected Achievements (from tailor's top_bullets).
    if include_top_bullets:
        top_bullets = generated_json.get("top_bullets") or []
        bullet_strs: list[str] = []
        for b in top_bullets:
            if isinstance(b, str):
                bullet_strs.append(b)
            elif isinstance(b, dict):
                txt = b.get("text") or ""
                if txt:
                    bullet_strs.append(txt)
        if bullet_strs:
            sections["Selected Achievements"] = bullet_strs

    # Experience.
    positions = generated_json.get("positions") or []
    if positions:
        sections["Experience"] = [_experience_entry(p) for p in positions]

    # Skills.
    skills_lines = _skills_section(generated_json.get("skills_grid"))
    if skills_lines:
        sections["Skills"] = skills_lines

    # Education.
    education = generated_json.get("education") or []
    if education:
        sections["Education"] = [_education_entry(e) for e in education]

    # Certifications.
    cert_lines = _certs_section(generated_json.get("certifications"))
    if cert_lines:
        sections["Certifications"] = cert_lines

    design = {"theme": theme}

    return {"cv": cv_dict, "design": design}


def coin_to_rendercv_model(
    generated_json: dict,
    *,
    theme: str = "engineeringresumes",
    output_dir: Path | None = None,
    output_basename: str | None = None,
    include_summary: bool = True,
    include_top_bullets: bool = True,
):
    """Build a RenderCVModel ready for rendercv.renderer.typst.generate_typst().

    output_dir + output_basename override the rendercv_settings paths so
    artifacts land where coin wants them (data/resumes/generated/).
    """
    from rendercv.schema.rendercv_model_builder import build_rendercv_dictionary_and_model
    import yaml

    yaml_dict = coin_to_rendercv_dict(
        generated_json,
        theme=theme,
        include_summary=include_summary,
        include_top_bullets=include_top_bullets,
    )

    yaml_str = yaml.safe_dump(yaml_dict, sort_keys=False, allow_unicode=True)
    _, model = build_rendercv_dictionary_and_model(yaml_str)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        slug = output_basename or re.sub(
            r"[^a-z0-9]+", "_",
            (generated_json.get("name") or "cv").lower(),
        ).strip("_")
        model.settings.render_command.output_folder = output_dir
        model.settings.render_command.typst_path = output_dir / f"{slug}.typ"
        model.settings.render_command.pdf_path = output_dir / f"{slug}.pdf"
        model.settings.render_command.markdown_path = output_dir / f"{slug}.md"
        model.settings.render_command.html_path = output_dir / f"{slug}.html"
        model.settings.render_command.png_path = output_dir / f"{slug}.png"
        # Skip extra outputs we don't need.
        model.settings.render_command.dont_generate_markdown = True
        model.settings.render_command.dont_generate_html = True
        model.settings.render_command.dont_generate_png = True

    return model


# ── Theme dispatch via config/profile.yml ───────────────────────────────

def themes_for_lane(lane_slug: str, profile_yml: dict | None = None) -> dict[str, list[str]]:
    """Return {primary, alts: [...]} for a lane. Reads config/profile.yml.

    Falls back to defaults if the lane isn't configured."""
    if profile_yml is None:
        import yaml
        yml_path = ROOT / "config" / "profile.yml"
        profile_yml = yaml.safe_load(yml_path.read_text()) or {}

    archetypes = profile_yml.get("archetypes", {}) or {}
    lane = archetypes.get(lane_slug, {}) or {}
    rcv = lane.get("rendercv_themes") or {}

    # Defaults from the plan.
    DEFAULTS = {
        "mid-market-tpm": {"primary": "engineeringresumes", "alts": ["classic", "harvard"]},
        "enterprise-sales-engineer": {"primary": "classic", "alts": ["moderncv", "sb2nov"]},
        "iot-solutions-architect": {"primary": "engineeringclassic", "alts": ["engineeringresumes", "ink"]},
        "revenue-ops-operator": {"primary": "sb2nov", "alts": ["classic", "opal"]},
    }

    if "primary" in rcv:
        return {
            "primary": rcv["primary"],
            "alts": rcv.get("alts") or [],
        }
    return DEFAULTS.get(lane_slug, {"primary": "engineeringresumes", "alts": ["classic"]})
