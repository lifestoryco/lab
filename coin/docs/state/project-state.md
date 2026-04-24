# Coin — Project State

## What Was Just Done (2026-04-24)

### Initial scaffold ✅ COMPLETE

**New files:** Full project structure — see directory layout in CLAUDE.md
**Commits:** (initial)
**Decisions:** Python + SQLite for Phase 1 (no external DB deps); prompt caching on all transformer calls; Rich for terminal output matching holo aesthetic

---

## Active Blockers

None.

---

## Roadmap

| Task | Description | Status |
|------|-------------|--------|
| S-1.1 | Scraper: LinkedIn + Indeed working results | 🚧 Pending |
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
