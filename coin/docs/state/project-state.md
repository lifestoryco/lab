# Coin — Project State

## What Was Just Done (2026-04-24)

### Environment setup ✅ COMPLETE

**New files:** `.env` (local only), `data/db/pipeline.db` (gitignored)
**Commits:** none (setup artifacts are gitignored)
**Decisions:** Using Python 3.13 (Homebrew) — system Python is 3.9, not compatible
**Tests:** 6/6 passing

### Initial scaffold ✅ COMPLETE

**New files:** Full project structure — see directory layout in CLAUDE.md
**Commits:** 2dff486 — feat: scaffold coin — agentic career ops engine
**Decisions:** Python + SQLite for Phase 1 (no external DB deps); prompt caching on all transformer calls; Rich for terminal output matching holo aesthetic

---

## Next Session Agenda

1. Run `/alpha-squad` on the full system design — get 7-advisor critique before writing more code
2. Refine the 3 target lanes based on alpha squad output
3. Tackle S-1.1: get the scraper returning live results

## Active Blockers

- `ANTHROPIC_API_KEY` must be added to `coin/.env` before any Claude API calls work
- System Python is 3.9 — always use `.venv/bin/python` (built on Python 3.13 via Homebrew)

---

## Roadmap

| Task | Description | Status |
|------|-------------|--------|
| S-1.1 | Scraper: LinkedIn + Indeed working results | ▶️ Up Next |
| S-1.2 | Analyzer: JD parsing via Claude API | 🚧 Pending |
| S-1.3 | Transformer: lane-aware resume rewriting | 🚧 Pending |
| S-1.4 | Pipeline DB: CRUD + dashboard rendering | 🚧 Pending |
| S-1.5 | Compensation: Levels.fyi cross-reference | 🚧 Pending |
| S-2.1 | Resume quality: PDF output via weasyprint | 🔲 Backlog |
| S-2.2 | Comp intelligence: Glassdoor band scraping | 🔲 Backlog |
| S-2.3 | Cover letter: full draft generation | 🔲 Backlog |
| S-3.1 | Scheduler: daily auto-search cron | 🔲 Backlog |
| S-3.2 | Multi-board: Greenhouse / Lever / Workday | 🔲 Backlog |

---

## Resolved Bugs

None yet.

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite over Postgres | Zero external deps in Phase 1; migrate if needed in Phase 3 |
| claude-sonnet-4-6 for transformer | Best quality/cost for resume writing; haiku for classification |
| Prompt caching on profile JSON | Profile is large and stable — saves tokens on every transformer call |
| httpx over requests | Async-ready, modern, handles HTTP/2 |
