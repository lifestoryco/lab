# Coin — Project State

## What Was Just Done (2026-04-25, Session 4 — Part 5)

### /code-review --fix pass: ALL severities resolved ✅ COMPLETE

**Tests:** 98/98 pass (up from 83/91; 7 net new tests, 8 stale assertions corrected, 0 regressions).

**Group A — Audit hardening (modes/audit.md):**
- Check 3: positive-test rule (Cox/TitanX/Safeguard MUST contain Hydrant framing) + verb list expanded (ran/headed/spearheaded/architected/championed)
- Check 4 escalated WARN→CRITICAL; trigger list +12 phrases (NASDAQ:, hypergrowth, mission-critical, multi-billion, etc.)
- Check 5 broadened: numeric + spelled-out + collective-noun + team-shape + tenure all require source
- Check 7 removed mid-market-tpm exemption — target_role now required for every lane
- Orthogonality "trumps" rules added per check

**Group B — Tailor mode aligned (modes/tailor.md):**
- 5 → 4 archetypes
- target_role required (with per-lane table)
- Self-audit step 7 added
- Audit-aware writing rules section (7 rules tracking the 9 checks)

**Group C — 3 phantom modes built:**
- modes/followup.md (cadence tracker, 7d/14d/21d windows)
- modes/patterns.md (rejection cluster analysis with lane×tier×grade pivot)
- modes/interview-prep.md (round-aware brief: recruiter/HM/technical/panel/final)

**Group D — commands/coin.md regenerated** (4 archetypes, 16 modes, current routing).

**Group E — Render hardening (scripts/render_pdf.py + config.py):**
- Jinja2 `Environment(autoescape=select_autoescape(['html']))` replaces raw `Template()`
- WeasyPrint `base_url` scoped to `data/` (was `cwd` → file:// could read .env)
- RECRUITER_TEMPLATE_PATH moved to config.py
- Dead branch in out_path collapsed to single line
- Wrapped-JSON missing key now raises (was silent fallback)
- target_role wired through template; recruiter HTML uses `header_role or profile.title`

**Group F — Scoring fixes (careerops/score.py + careerops/pipeline.py):**
- score_breakdown: early-return composite=0/grade=F when lane='out_of_band' OR lane not in LANES (kills resurrection bug part 1)
- upsert_role: ON CONFLICT now uses CASE WHEN roles.lane='out_of_band' THEN 0 (kills resurrection bug part 2)
- score_company_tier: bidirectional substring → one-direction word-boundary match
- Added update_lane(), update_role_notes() helpers
- Stale weights docstring updated

**Group G — test_score.py inversion alignment:**
- 8 stale assertions rewritten (FAANG=100 → FAANG=25, default=45 → default=65)
- 4 new defensive tests added (out_of_band quarantine, unknown lane treated as quarantine, FAANG-LOWER-than-unknown inversion proof, substring safety)
- All 44 score tests pass

**Group H — Hygiene:**
- .env.example floors updated 180K/250K → 160K/200K
- target_locations dropped from base.py PROFILE; profile.yml is canonical (new get_target_locations() helper)
- scripts/migrations/001_archetypes_5_to_4.py: idempotent, tracked in schema_migrations table, applied successfully

**Group I — Audit fixture isolated:**
- tests/fixtures/audit/0137_filevine_se_known_bad.json (frozen copy)
- /coin pdf 137 in dev no longer overwrites the regression baseline

**Group J — Auto-pipeline hardened:**
- LinkedIn search-URL detection (rejects /jobs/search?keywords=... before wasting fetch_jd)
- Per-ATS URL pattern table for the URL ingest step
- Audit-fix oscillation diagnostic (detects ping-pong between competing checks; never runs 3rd iteration)

**Group K — Operating infrastructure:**
- .claude/settings.json with 30+ permission allowlist entries (Python venv calls, sqlite3 reads, git read-only, common file ops) + 8 deny rules (rm -rf, force-push, hard-reset, curl|sh)
- Removed unused agents: frontend-engineer.md, devops-engineer.md (Python+SQLite stack)
- Adapted db-architect.md from Postgres+RLS to SQLite + quarantine-aware
- New python-engineer.md agent (coin-stack-specific)

**Open follow-ups (deferred, low priority):**
- COIN-NETWORK-SCAN: port proficiently network-scan skill (LinkedIn warm-intro discovery)
- COIN-OFERTAS: port santifer multi-offer comparison mode
- COIN-COVER-LETTER: port proficiently cover-letter as separate mode (currently folded into tailor)
- COIN-AUTO-PIPELINE-EXECUTABLE: convert SKILL.md narrative onboarding to actual AskUserQuestion blocks

---

## What Was Just Done (2026-04-25, Session 4 — Part 4)

### Mode build-out + _shared.md refresh ✅ COMPLETE

**3 task prompts authored, executed, and shipped:**
- `COIN-AUDIT` → `modes/audit.md` (159 lines, 9 truthfulness checks) + `tests/test_audit_mode.py` (10 passing)
- `COIN-AUTOPIPELINE` → `modes/auto-pipeline.md` (200+ lines, 8 strict steps) + `tests/test_auto_pipeline.py` (14 passing)
- `COIN-APPLY` → `modes/apply.md` (200+ lines, 6 hard refusals) + `tests/test_apply_mode.py` (19 passing)

**modes/_shared.md refreshed:**
- 5 archetypes → 4 (current truth)
- Comp floor $180K/$250K → $160K/$200K
- Company tier scoring documented as INVERTED (FAANG penalized for Sean)
- Truthfulness gates promoted from implicit to explicit Operating Principle #3
- Out-of-band quarantine + the known resurrection bug documented
- Mode catalog cross-references all 9 active modes
- Open-follow-ups list captures: SCORE-TESTS, QUARANTINE-RESURRECTION, PIPELINE-HELPERS, TAILOR-FORCE, EMAIL-CANONICAL

**Tests:** 83 pass / 8 pre-existing failures (all in test_score.py, all from the company_tier
inversion done earlier this session — covered by COIN-SCORE-TESTS follow-up).

**Decisions:** Mode authoring done as prompt-driven markdown (no Python implementation).
The agent reads the mode at execution time. This keeps the LLM-as-runtime model intact
while still allowing structural regression tests (each test asserts the mode markdown
contains required sections, refusals, gates).

---

## What Was Just Done (2026-04-25, Session 4 — Part 1)

### COIN-AUDIT — modes/audit.md (truthfulness check) ✅ COMPLETE

**New files:**
- `modes/audit.md` (159 lines) — 9-check truthfulness audit with auto-fix flow + human gate
- `tests/test_audit_mode.py` (10 tests) — structural + regression tests against the known-bad Filevine JSON
- `docs/tasks/prompts/complete/COIN-AUDIT_04-25_modes-audit.md` — task prompt

**Tests:** 10/10 audit tests pass. Pre-existing 8 failures in `test_score.py` are from
this session's earlier company_tier inversion (FAANG 100 → 25 as pedigree filter); not
caused by COIN-AUDIT. Needs follow-up task `COIN-SCORE-TESTS` to update assertions.

**Decisions:** 9 audit checks encoded directly from the 2026-04-24 code review's CRITICAL/HIGH
findings. Each check has an explicit fail condition, severity, and fix template — refusing
to soften them is a hard rule.

---

## What Was Just Done (2026-04-25, Session 3 — Part 3)

### santifer feature parity: scoring richness + liveness + PDF ✅ COMPLETE

**4 features added:**

**1. 8-dimension scoring with A-F grades** (`config.py`, `careerops/score.py`):
- Old: 4 dimensions (comp, skill, title, remote)
- New: 8 dimensions — added `company_tier` (FAANG+ vs unicorn vs unknown),
  `application_effort` (LinkedIn easy vs ATS vs custom), `seniority_fit`
  (staff/principal vs senior vs junior), `culture_fit` (red flag count)
- New `score_breakdown()` returns per-dimension raw scores, weights, and
  contributions — useful for diagnosing why a role scored low
- New `score_grade()` converts composite to A–F (A≥85, B≥70, C≥55, D≥40, F<40)
- Netflix TPM Infrastructure: 76.1 → **80.0 (B)** under new weights
- Tests: 20 → **48 passing**

**2. Dashboard shows Grade column** (`careerops/pipeline.py`):
- Fit column still present; Grade column added with color coding
  (bold green=A, green=B, yellow=C, red=D, dim red=F)

**3. Liveness check** (`scripts/liveness_check.py`):
- Pings all non-terminal roles; marks `closed` if HTTP 404 or JD removal
  phrases detected. `--dry-run` flag for report-only mode.
- System dep: requires `httpx` (already in deps)

**4. PDF generation** (`scripts/render_pdf.py`, `data/resume_template.html`):
- Reads generated resume JSON, renders via Jinja2 HTML template, writes
  print-ready PDF via weasyprint
- System dep: requires `brew install pango` (one-time, done on this machine)
- First PDF: `data/resumes/generated/0004_cox-style-tpm_2026-04-25.pdf`
- `requirements.txt` now includes `jinja2>=3.1.0`

---

## What Was Just Done (2026-04-25, Session 3 — Part 2)

### First end-to-end run on new machine ✅ COMPLETE

**Goal:** Set up Coin on new machine, fix bugs found during first live run, execute
full discover → score → tailor pipeline.

**Setup:**
- Created `.venv/` at `/Users/tealizard/Documents/lab/coin/`
- Installed all deps from `requirements.txt` — 20/20 tests pass
- Fixed stale path `/Users/sean/Documents/Handoffpack/...` → `/Users/tealizard/Documents/lab/coin/` in `SKILL.md` and `modes/_shared.md`

**Bug fixed — comp-blindness in score_fit:**
- `score_fit()` was reading `comp_min`/`comp_max` from the DB row only, ignoring the
  parsed JD. When the JD has `comp_explicit=True`, the real comp was silently dropped,
  collapsing every explicitly-priced role to score 55 (unverified penalty).
- Fix 1: `score.py` — fallback to `parsed_jd["comp_min"]` when DB row comp is null
  and `comp_explicit` is True.
- Fix 2: `pipeline.py` `update_jd_parsed()` — now also persists `comp_min`/`comp_max`
  to the DB row when `comp_explicit=True`, so subsequent calls don't need the fallback.

**Live discovery:** 32 roles across all 5 archetypes, all active in pipeline.

**First resume generated:**
- Role: Netflix "Technical Program Manager - Infrastructure Engineering"
- Comp: $420K–$630K (explicitly stated in JD)
- Fit score: 76.1 (was 58.1 before comp-blindness fix)
- Saved to `data/resumes/generated/0004_cox-style-tpm_2026-04-25.json`
- Status: `resume_generated`

---

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

1. **Submit the Netflix application.** Resume + PDF are generated:
   `data/resumes/generated/0004_cox-style-tpm_2026-04-25.{json,pdf}`.
   Sean reviews, applies, then: `/coin track 4 applied`.
2. **Score + tailor the Netflix TPM 6 — Data Systems role** — same company,
   different infra focus; $420K–$630K comp range expected.
3. **Re-score all 31 existing roles** under the new 8-dimension weights —
   run: `python scripts/discover.py --rescore-existing` (not yet wired) or
   inline Python loop against `list_roles()`.
4. **Add comp extraction to scraper** — most roles have null comp_min;
   cross-reference Levels.fyi for Tier 1 companies.

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
