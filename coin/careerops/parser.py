"""Clean-room PDF resume parser — 4-step deterministic heuristic.

This module is a clean-room Python re-implementation of the algorithm
described publicly in OpenResume's "Resume Parser Algorithm Deep Dive"
(https://www.open-resume.com/resume-parser). NO code from OpenResume is
copied — we implement the same documented heuristic from scratch using
pypdfium2 (MIT) for PDF I/O.

The 4 steps:
  1. Extract text items with (x, y, height, width) metadata.
  2. Group items into lines by vertical proximity.
  3. Detect section headers by font size + UPPERCASE + sole-on-line +
     canonical-label fallback.
  4. Extract canonical fields (name, email, phone, dates, url) by
     feature-scored regex/predicate ensemble. Highest-scoring candidate
     wins.

Two consumers:
  - ATS self-check: re-parse our own rendered PDF; extraction completeness
    drives `render_artifact.ats_score`.
  - Onboarding ingestion: extract experience from a user-provided PDF
    (LinkedIn export, brag doc) and seed the `accomplishment` table.

Output: a structured ParseResult. The score (0-100) is the key signal
for ATS-readiness.

NOT in scope: OCR for scanned PDFs (text-only). Multi-page weird layouts.
Two-column resumes (we handle them but Y-grouping may merge cross-column).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ── Public dataclasses ──────────────────────────────────────────────────

@dataclass
class TextItem:
    text: str
    x: float        # left edge
    y: float        # bottom edge in page-local coords (PDF: higher = up)
    width: float
    height: float   # font size proxy
    page_idx: int = 0

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y + self.height

    def reading_order_key(self) -> tuple[int, float, float]:
        """Page-major reading order (page asc, then top→bottom, then left→right)."""
        return (self.page_idx, -self.y, self.x)


@dataclass
class TextLine:
    items: list[TextItem]
    y: float
    text: str
    avg_height: float

    def is_uppercase_only(self) -> bool:
        cleaned = re.sub(r"[^A-Za-z]", "", self.text)
        return bool(cleaned) and cleaned.isupper()

    def is_short(self, max_chars: int = 30) -> bool:
        return len(self.text.strip()) <= max_chars


@dataclass
class Section:
    label: str
    canonical: str       # 'experience' | 'education' | 'skills' | 'projects' | etc.
    start_line: int
    end_line: int
    lines: list[TextLine]


@dataclass
class ParsedField:
    """Extracted canonical field with the candidate that won feature scoring."""
    field: str           # 'name' | 'email' | 'phone' | 'url' | 'location'
    value: str
    confidence: float    # 0..1 (winner's score normalized)


@dataclass
class ParseResult:
    text_items: list[TextItem]
    lines: list[TextLine]
    sections: list[Section]
    fields: dict[str, ParsedField]
    raw_text: str
    n_pages: int

    def ats_score(self) -> int:
        """Percentage of canonical signals successfully extracted (0-100).

        The score is the practical ATS-readiness signal: if our deterministic
        parser can extract everything, an ATS will too.
        """
        signals = {
            "name": "name" in self.fields,
            "email": "email" in self.fields,
            "phone": "phone" in self.fields,
            "experience_section": any(s.canonical == "experience" for s in self.sections),
            "education_section": any(s.canonical == "education" for s in self.sections),
            "skills_section": any(s.canonical == "skills" for s in self.sections),
            "has_dated_bullets": _at_least_n_dated_lines(self.lines, n=3),
            "monocolumn_text_density": _looks_monocolumn(self.lines),
            "no_unicode_glyph_garbage": _no_unicode_glyph_garbage(self.raw_text),
            "page_count_reasonable": self.n_pages in (1, 2),
        }
        hit = sum(1 for v in signals.values() if v)
        return int(round(100 * hit / len(signals)))

    def section_canonicals(self) -> set[str]:
        return {s.canonical for s in self.sections}


# ── Constants ───────────────────────────────────────────────────────────

CANONICAL_SECTION_LABELS = {
    "experience": [
        "experience", "work experience", "professional experience",
        "employment", "employment history", "work history",
        "professional history", "career history", "selected experience",
    ],
    "education": [
        "education", "academic background", "academic history",
    ],
    "skills": [
        "skills", "technical skills", "core skills", "competencies",
        "key skills", "technical proficiencies", "tools",
    ],
    "projects": [
        "projects", "selected projects", "notable projects",
        "side projects", "personal projects",
    ],
    "summary": [
        "summary", "professional summary", "executive summary",
        "profile", "about", "objective",
    ],
    "certifications": [
        "certifications", "certificates", "licenses",
    ],
    "publications": [
        "publications", "papers", "presentations",
    ],
    "awards": [
        "awards", "honors", "recognition", "achievements",
    ],
}

# Reverse lookup: phrase → canonical.
_LABEL_TO_CANONICAL: dict[str, str] = {
    phrase.lower(): canon
    for canon, phrases in CANONICAL_SECTION_LABELS.items()
    for phrase in phrases
}


# ── Step 1: extract text items ──────────────────────────────────────────

def extract_text_items(pdf_path: str | Path) -> tuple[list[TextItem], int]:
    """Extract per-line TextItem entries from the PDF.

    Approach: use PDFium's `get_text_range(0, -1)` to get the full page
    text in reading order (PDFium handles internal char clustering for
    us). Split by line breaks. For each non-empty line, use the first
    char's charbox to anchor X/Y/height.

    This dodges the descender-fragmentation problem we'd hit by
    iterating chars one-at-a-time.

    Returns (items, n_pages).
    """
    import pypdfium2 as pdfium

    items: list[TextItem] = []
    pdf = pdfium.PdfDocument(str(pdf_path))
    n_pages = len(pdf)

    try:
        for page_idx in range(n_pages):
            page = pdf[page_idx]
            try:
                tp = page.get_textpage()
            except Exception:
                continue
            try:
                n_chars = tp.count_chars()
            except Exception:
                continue
            if n_chars == 0:
                continue

            # PDFium returns full page text with embedded \r\n line breaks.
            try:
                full = tp.get_text_range(0, -1)
            except Exception:
                continue

            if not full:
                continue

            # Walk through the string char-by-char to track which
            # source-PDF char index each output char corresponds to.
            # This is essential because get_text_range may insert
            # whitespace glue or normalize chars; the char index in the
            # original PDFium textpage is what get_charbox needs.
            #
            # We assume a 1:1 mapping between output chars and source
            # chars in `full` (PDFium typically preserves this). Splits
            # happen on `\r\n` or `\n` runs.

            char_idx = 0
            line_buffer: list[tuple[str, int]] = []   # (char, source_index)
            for ch in full:
                if ch in "\r\n":
                    if line_buffer:
                        items.extend(_emit_line(line_buffer, tp, page_idx))
                        line_buffer = []
                    char_idx += 1
                    continue
                line_buffer.append((ch, char_idx))
                char_idx += 1
            if line_buffer:
                items.extend(_emit_line(line_buffer, tp, page_idx))
    finally:
        pdf.close()

    items = [it for it in items if it.text.strip()]
    return items, n_pages


def _emit_line(
    line_buffer: list[tuple[str, int]],
    tp,
    page_idx: int,
) -> list[TextItem]:
    """Emit one TextItem per visual line.

    Use the bounding boxes of the first/last visible chars on the line
    for x/y/width/height. Approximate height via charbox top-bottom on
    the first non-space char.
    """
    if not line_buffer:
        return []
    line_text = "".join(c for c, _ in line_buffer).rstrip()
    if not line_text.strip():
        return []

    # Find first non-space char to anchor position.
    anchor = None
    for ch, idx in line_buffer:
        if ch.strip():
            try:
                box = tp.get_charbox(idx)
            except Exception:
                continue
            if box and any(abs(v) > 0.001 for v in box):
                anchor = (idx, box)
                break
    if anchor is None:
        return []

    # Find last non-space char for the right edge.
    last_box = None
    for ch, idx in reversed(line_buffer):
        if ch.strip():
            try:
                box = tp.get_charbox(idx)
            except Exception:
                continue
            if box and any(abs(v) > 0.001 for v in box):
                last_box = box
                break

    a_left, a_bottom, a_right, a_top = anchor[1]
    if last_box is not None:
        right = last_box[2]
    else:
        right = a_right

    item = TextItem(
        text=line_text,
        x=a_left,
        y=a_bottom,
        width=max(right - a_left, 0.0),
        height=max(a_top - a_bottom, 0.0),
        page_idx=page_idx,
    )
    return [item]


# ── Step 2: group items into lines ──────────────────────────────────────

def group_items_into_lines(items: Iterable[TextItem]) -> list[TextLine]:
    items_sorted = sorted(items, key=lambda it: it.reading_order_key())
    lines: list[TextLine] = []
    current: list[TextItem] = []
    current_y: float | None = None
    current_page: int | None = None

    for it in items_sorted:
        same_page = current_page is None or it.page_idx == current_page
        same_line = (
            same_page
            and current_y is not None
            and abs(it.y - current_y) < 2.0
        )
        if same_line:
            current.append(it)
        else:
            if current:
                lines.append(_finalize_line(current))
            current = [it]
            current_y = it.y
            current_page = it.page_idx
    if current:
        lines.append(_finalize_line(current))

    return lines


def _finalize_line(items: list[TextItem]) -> TextLine:
    items_sorted = sorted(items, key=lambda it: it.x)
    text = " ".join(it.text for it in items_sorted).strip()
    text = re.sub(r"\s+", " ", text)
    avg_h = sum(it.height for it in items_sorted) / max(len(items_sorted), 1)
    return TextLine(
        items=items_sorted,
        y=items_sorted[0].y if items_sorted else 0.0,
        text=text,
        avg_height=avg_h,
    )


# ── Step 3: detect sections ─────────────────────────────────────────────

def detect_sections(lines: list[TextLine]) -> list[Section]:
    """Detect section headers + assemble Section objects.

    Heuristic (OpenResume-style):
    1. Canonical-label match (case-insensitive). Highest priority.
    2. Larger-than-body-text font height + UPPERCASE + ≤30 chars on a line by itself.

    The Section runs from the header line to the next header line (or end).
    """
    if not lines:
        return []

    # Estimate body-text font height: median of all line heights weighted
    # by occurrence count.
    heights = sorted([round(ln.avg_height, 1) for ln in lines if ln.avg_height > 0])
    body_h = heights[len(heights) // 2] if heights else 10.0

    headers: list[tuple[int, str]] = []  # (line_index, canonical)
    for i, ln in enumerate(lines):
        canon = _classify_section_header(ln, body_h)
        if canon:
            headers.append((i, canon))

    sections: list[Section] = []
    for k, (start, canon) in enumerate(headers):
        end = headers[k + 1][0] if (k + 1) < len(headers) else len(lines)
        sec_lines = lines[start + 1:end]
        sections.append(Section(
            label=lines[start].text,
            canonical=canon,
            start_line=start,
            end_line=end - 1,
            lines=sec_lines,
        ))
    return sections


def _classify_section_header(line: TextLine, body_height: float) -> str | None:
    """Return canonical label if this line is a section header, else None."""
    text_norm = line.text.strip().rstrip(":").lower()
    if not text_norm:
        return None

    # Canonical-label match wins.
    if text_norm in _LABEL_TO_CANONICAL:
        return _LABEL_TO_CANONICAL[text_norm]
    # Allow a couple of characters of slack at edges (trailing dash, dot, em-dash).
    text_norm_stripped = re.sub(r"^[^A-Za-z]+|[^A-Za-z]+$", "", text_norm)
    if text_norm_stripped in _LABEL_TO_CANONICAL:
        return _LABEL_TO_CANONICAL[text_norm_stripped]

    # Visual signals: large font + UPPERCASE + short.
    is_larger = line.avg_height >= body_height * 1.15
    if is_larger and line.is_uppercase_only() and line.is_short(max_chars=30):
        # Even when not a canonical label, classify visually.
        # Map a few common headers to canonical anyway by substring.
        for canon, phrases in CANONICAL_SECTION_LABELS.items():
            for phrase in phrases:
                if phrase in text_norm:
                    return canon
        return text_norm  # custom header — preserved verbatim.
    return None


# ── Step 4: feature-scored field extraction ─────────────────────────────

# Feature predicates: (predicate, score). Score sums per candidate;
# highest-scoring candidate wins for the field.

_RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_RE_URL = re.compile(r"\b(?:https?://|linkedin\.com/in/|github\.com/)[\w./\-?=&%#:]+", re.IGNORECASE)
_RE_PHONE_LOOSE = re.compile(
    r"(?<!\d)(?:\+?1[\.\-\s]?)?\(?\d{3}\)?[\.\-\s]?\d{3}[\.\-\s]?\d{4}(?!\d)",
)
_RE_DATE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)(?:[a-z]*)\s*\d{4}\b",
    re.IGNORECASE,
)
_RE_LOCATION = re.compile(
    r"\b([A-Z][a-z]+(?:[\-\s][A-Z][a-z]+)*),\s+([A-Z]{2}|[A-Z][a-z]+)\b",
)


def _looks_like_name(line: TextLine, *, body_height: float) -> int:
    """Score a line as a potential name."""
    score = 0
    text = line.text.strip()
    if not text:
        return 0
    if "@" in text or _RE_PHONE_LOOSE.search(text) or _RE_URL.search(text):
        score -= 6
    if line.avg_height >= body_height * 1.4:
        score += 5
    elif line.avg_height >= body_height * 1.15:
        score += 2
    n_words = len(text.split())
    if 2 <= n_words <= 4:
        score += 3
    elif n_words >= 6:
        score -= 2
    if any(c.islower() for c in text):
        score += 1  # mixed case is name-like (vs ALL CAPS)
    if re.search(r"\d", text):
        score -= 3
    return score


def extract_fields(lines: list[TextLine]) -> dict[str, ParsedField]:
    """Run feature-scored field extraction across the first ~10 lines
    (typical contact-block region) plus document-wide regex matches."""
    fields: dict[str, ParsedField] = {}
    if not lines:
        return fields

    body_heights = sorted([round(ln.avg_height, 1) for ln in lines if ln.avg_height > 0])
    body_h = body_heights[len(body_heights) // 2] if body_heights else 10.0

    # Email — first match wins (resumes typically show only one).
    for ln in lines:
        m = _RE_EMAIL.search(ln.text)
        if m:
            fields["email"] = ParsedField(field="email", value=m.group(0), confidence=1.0)
            break

    # Phone — first plausible match wins.
    for ln in lines:
        m = _RE_PHONE_LOOSE.search(ln.text)
        if m:
            fields["phone"] = ParsedField(field="phone", value=m.group(0), confidence=0.95)
            break

    # URL — first match wins.
    for ln in lines:
        m = _RE_URL.search(ln.text)
        if m:
            fields["url"] = ParsedField(field="url", value=m.group(0), confidence=0.9)
            break

    # Name — feature-scored across top 10 lines.
    name_candidates: list[tuple[float, str]] = []
    for ln in lines[:10]:
        score = _looks_like_name(ln, body_height=body_h)
        if score > 0:
            name_candidates.append((float(score), ln.text.strip()))
    if name_candidates:
        name_candidates.sort(reverse=True)
        winner_score, winner_text = name_candidates[0]
        fields["name"] = ParsedField(
            field="name",
            value=winner_text,
            confidence=min(1.0, winner_score / 9.0),
        )

    # Location — first plausible match wins.
    for ln in lines[:15]:
        m = _RE_LOCATION.search(ln.text)
        if m:
            fields["location"] = ParsedField(
                field="location", value=m.group(0), confidence=0.85,
            )
            break

    return fields


# ── ATS-readiness predicates ────────────────────────────────────────────

def _at_least_n_dated_lines(lines: list[TextLine], *, n: int = 3) -> bool:
    return sum(1 for ln in lines if _RE_DATE.search(ln.text)) >= n


def _looks_monocolumn(lines: list[TextLine]) -> bool:
    """Detect 'native columns' (good) vs 'tables faking columns' (bad).

    Good signal: most lines start near the same x-coordinate, with low
    standard deviation. If the lines bimodally start at two distinct x-
    coordinates (left + right column), the parser has likely interleaved
    cross-column rows — bad for ATS. We're approximate here; the real
    test is whether downstream extraction works.
    """
    xs = [ln.items[0].x for ln in lines if ln.items]
    if len(xs) < 5:
        return True
    # Round to 5pt bins.
    bins: dict[int, int] = {}
    for x in xs:
        bins[int(x // 5)] = bins.get(int(x // 5), 0) + 1
    # Top 1 bin should hold ≥40% of lines for monocolumn-like layout.
    top = max(bins.values())
    return (top / len(xs)) >= 0.40


_GLYPH_GARBAGE_RE = re.compile(r"[-]")  # private-use area = font icons


def _no_unicode_glyph_garbage(raw_text: str) -> bool:
    return _GLYPH_GARBAGE_RE.search(raw_text) is None


# ── Top-level entrypoint ────────────────────────────────────────────────

def parse_resume_pdf(pdf_path: str | Path) -> ParseResult:
    """Parse a resume PDF end-to-end. Deterministic, zero-API-call."""
    items, n_pages = extract_text_items(pdf_path)
    lines = group_items_into_lines(items)
    sections = detect_sections(lines)
    fields = extract_fields(lines)
    raw_text = "\n".join(ln.text for ln in lines)
    return ParseResult(
        text_items=items,
        lines=lines,
        sections=sections,
        fields=fields,
        raw_text=raw_text,
        n_pages=n_pages,
    )


# ── CLI ────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path", help="Path to a resume PDF")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = ap.parse_args()

    p = Path(args.pdf_path)
    if not p.exists():
        print(f"❌ Not found: {p}", file=sys.stderr)
        return 1

    result = parse_resume_pdf(p)
    if args.json:
        out = {
            "ats_score": result.ats_score(),
            "n_pages": result.n_pages,
            "n_lines": len(result.lines),
            "n_sections": len(result.sections),
            "sections": [
                {"label": s.label, "canonical": s.canonical, "n_lines": len(s.lines)}
                for s in result.sections
            ],
            "fields": {k: {"value": v.value, "confidence": v.confidence} for k, v in result.fields.items()},
        }
        print(json.dumps(out, indent=2))
        return 0

    print(f"Pages: {result.n_pages}  Lines: {len(result.lines)}  Sections: {len(result.sections)}")
    print(f"ATS readiness score: {result.ats_score()}/100")
    print()
    print("Extracted fields:")
    for k, v in result.fields.items():
        print(f"  {k}: {v.value!r} (conf {v.confidence:.2f})")
    print()
    print("Sections:")
    for s in result.sections:
        print(f"  [{s.canonical}] {s.label!r} ({len(s.lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
