# Coin — Project State

## What Was Just Done (2026-04-24, Session 2)

### Alpha-Squad rearchitecture ✅ COMPLETE

**Goal:** Eliminate Anthropic API dependency so Coin runs entirely inside
Sean's Claude Code subscription. Borrow heavily from santifer/career-ops.

**New files:**
- `.claude/skills/coin/SKILL.md` — modal router
- `modes/_shared.md, discover.md, score.md, tailor.md, track.md, status.md, url.md`
- `config/profile.yml` — 5 Sean-grounded archetypes with North Star pitches
- `careerops/score.py` — pure-Python fit scoring (comp-first weighting)
- `scripts/discover.py, print_role.py, save_resume.py, update_role.py, fetch_jd.py, dashboard.py`

**Deleted files:**
- `careerops/analyzer.py` (logic moved to `modes/score.md`)
- `careerops/transformer.py` (logic moved to `modes/tailor.md`)

**Rewritten files:**
- `config.py` — 3 coarse lanes → 5 archetypes (cox-style-tpm, titanx-style-pm,
  enterprise-sales-engineer, revenue-ops-transformation, global-eng-orchestrator)
- `careerops/scraper.py` — now hits LinkedIn guest API (public, no auth);
  live results confirmed (10+ real roles scraped and scored)
- `careerops/pipeline.py` — extended state machine (11 states from santifer);
  added list_roles, update_fit_score, update_jd_raw; Rich dashboard with
  comp-trajectory header
- `requirements.txt` — removed `anthropic`; added `pyyaml`, `httpx[http2]`, `h2`
- `.env.example` — removed `ANTHROPIC_API_KEY`; added `COIN_MIN_TC`, `COIN_LOCATION`
- `CLAUDE.md` — rewrote for skill-host architecture
- `.claude/commands/coin.md` — now a thin router that invokes the skill
- `.claude/commands/coin-{apply,search,setup,track}.md` — deleted (superseded by modal `/coin`)

**Tests:** 6/6 passing.
**Live verification:** `scripts/discover.py --lane cox-style-tpm --limit 10`
returns 10 real LinkedIn postings with titles, companies, locations, and
heuristic fit scores 65–83.

---

## Next Session Agenda

1. **Run `/coin` in Claude Code desktop** as Sean for real — first human-driven
   end-to-end: discover → pick one → score (JD parse) → tailor → file a real
   application.
2. **Refine one North Star pitch** based on how the first tailor output reads.
3. **Phase 2 kickoff:** port santifer's `claude -p` batch resumability for
   scoring 50+ roles in parallel.

## Active Blockers

None. No API key needed.

---

## Roadmap

| Task | Description | Status |
|------|-------------|--------|
| S-1.1 | Scraper: LinkedIn + Indeed live results | ✅ Done (LinkedIn live; Indeed Cloudflare-degraded as expected) |
| S-1.2 | Analyzer: JD parsing via Claude | ✅ Done (moved to `modes/score.md` — session-native) |
| S-1.3 | Transformer: lane-aware resume rewriting | ✅ Done (moved to `modes/tailor.md`) |
| S-1.4 | Pipeline DB: CRUD + dashboard | ✅ Done (11-state machine + Rich dashboard) |
| S-1.5 | Compensation: Levels.fyi cross-reference | 🚧 Pending — Phase 2 |
| S-2.1 | Resume quality: PDF via weasyprint | 🔲 Backlog |
| S-2.2 | Glassdoor comp band scraping | 🔲 Backlog |
| S-2.3 | Full cover letter generation (beyond hook) | 🔲 Backlog |
| S-2.4 | Batch resumability per santifer (claude -p workers) | 🔲 Backlog |
| S-3.1 | Scheduler: daily auto-search cron | 🔲 Backlog |
| S-3.2 | Multi-board: Greenhouse / Lever / Workday | 🔲 Backlog |

---

## Resolved Bugs

- httpx http2 support required explicit `h2` package install — added to requirements.
- Scripts couldn't find `careerops` module when invoked from `scripts/` dir
  → added `sys.path` bootstrap to each script (parent dir goes on path).
- `careerops/__init__.py` imported deleted `analyzer`/`transformer` modules
  → updated to export only current modules.

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Eliminate `anthropic` SDK | Sean has a Claude Code subscription; per-token billing is redundant. All LLM reasoning happens in the host session. |
| Modal skill router (santifer pattern) | One `/coin` entry beats a dozen flat `/coin-*` commands. Detects URL / mode keyword and dispatches. |
| Keep SQLite; reject markdown-as-DB | Coin already has pipeline.db and needs SQL ("fit ≥ 80 in lane X ordered by comp"). santifer uses .md files, which are greppable but not queryable. |
| 5 archetypes derived from Sean's real experience | 3 lanes (previous) were too coarse; 6 (santifer-parity) was overkill. Each archetype maps to a real proof point. |
| Comp-first fit weighting (comp 0.40, skills 0.30, title 0.20, remote 0.10) | Per CRO verdict in alpha-squad: comp delta is axis #1, not #3. |
| LinkedIn guest endpoint over scraping logged-in HTML | `jobs-guest/jobs/api/seeMoreJobPostings/search` is public, predictable, returns clean HTML cards. No cookie management. |
| Indeed best-effort (expect Cloudflare) | Rather than pull in Selenium/FlareSolverr, we let Indeed fail gracefully and rely on LinkedIn. Revisit with a paid scraping API if volume demands it. |
