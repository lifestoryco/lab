# Coin — Project State

## What Was Just Done (2026-04-26, Session 6 — Code-review --fix EVERYTHING + PDF redesign + DB persistence)

### /code-review (4-agent parallel) → all findings resolved + PDF beats rendercv reference ✅ COMPLETE

**Tests:** 223/223 pass (no new failures, no skipped). Verdict: PASS.

**Commits (6):**
- `6eb5d94` chore(coin): persist pipeline.db across worktrees + worktree-aware start
- `9d3b52d` fix(security): path-traversal guards across 5 scripts + shared helper
- `e062428` fix(coin): close quarantine resurrection + cover-letter Check 2 + utah-remote default
- `0cdcc84` feat(coin): init_db auto-runs migrations + careerops package surface
- `79caebe` chore(coin): drop unused pydantic + dateutil; complete mode catalog
- `3745ed5` feat(coin): Reactive-Resume sidebar PDF template + photo support + internal banner

**1. Persistent DB across worktrees**
- `config.py::DB_PATH` now defaults to `~/Library/Application Support/coin/pipeline.db` (macOS) / `$XDG_DATA_HOME/coin/` (Linux) / `%APPDATA%/coin/` (Windows). Always absolute. `COIN_DB_PATH` env override honored.
- 95 production roles migrated from in-tree `data/db/` to user-data dir; worktrees now share state.
- `scripts/start.sh` worktree-aware (uses `git rev-parse --show-toplevel`); reads DB_PATH from config rather than hardcoding `data/db/pipeline.db`.
- `init_db()` auto-runs `m001..m004` so a fresh DB lands on the latest schema (no more `no such table: outreach` first-run errors).

**2. Security path-traversal (1 CRIT + 2 HIGH + 2 MED + 1 LOW)**
- New `careerops/paths.py::validate_under(path, root, label)` — symlink-resolving, exits non-zero, used by every script that takes a user path.
- Guards added to: `render_pdf.py` (`--input`/`--out`), `save_resume.py` (`--input`), `update_role.py` (`--parsed-jd`), `import_linkedin_connections.py` (`--csv`).
- `track_outreach.py` SQL: f-string column-name interpolation replaced with static `_SQL_BY_ACTION` map (defense-in-depth alongside the existing `VALID_ACTIONS` whitelist).
- `pipeline.insert_offer` adds `assert set(cols).issubset(all_cols)` against future drift.

**3. Logic — quarantine resurrection (CRIT × 2, HIGH × 2, LOW × 1)**
- `pipeline._is_quarantined(lane)` helper: `lane == 'out_of_band' or lane not in LANES`. Both `upsert_role` ON CONFLICT and `update_lane` now sink fit_score=0 for ANY lane outside the 4 archetypes (closes the resurrection hole for legacy ids like `cox-style-tpm`).
- `upsert_role` COALESCE wrapped with `NULLIF(...,'')` (matches `network_scrape.upsert_scraped` contract).
- `modes/cover-letter.md` Check 2 was mislabeled (used Check 4's vague-flex content under the Pedigree non-claim label) → restored to audit Check 2 (no claim of FAANG/big-tech employment unless in PROFILE.positions).
- `scripts/discover.py` + `scripts/print_role.py`: stale `cox-style-tpm` → `mid-market-tpm` in docstrings.

**4. Architecture (3 HIGH + 6 MED + 4 LOW)**
- `careerops/__init__.py` exports `offer_math`, `network_scrape`, `paths`.
- `scripts/migrations/__init__.py` populated with `run_all(db_path)` + ordered `MIGRATIONS` list. m001 extracted public `apply()` (matches m002–m004); accepts both `001_…` and `m001_…` IDs in `_already_applied` for compat with existing DBs.
- `m002`/`m003`/`m004`: drop the manual `ROOT/DB_PATH` join now that `config.DB_PATH` is always absolute.
- `requirements.txt`: dropped unused `pydantic`, `python-dateutil`.
- `_shared.md` mode catalog completed: added `followup`, `patterns`, `interview-prep` (was 13 of 16); onboarding row corrected to "7 questions".
- `discover.py --utah-remote` default-on flag (memory-recorded scope that wasn't wired) with `--no-utah-remote` opt-out + consultancy blocklist (Big4 / Accenture / staff-aug shops).

**5. PDF redesign (CRIT × 1, HIGH × 4, MED × 4, LOW × 5)**
- `data/resume_template_recruiter.html` rewritten as Reactive-Resume "Azurill"-inspired: navy sidebar (`--accent: #0a3d62`) with optional 1.5in circular photo, name + creds, title, contact list, categorized Skills, Education, Certifications. Main column with Summary (rag-right), Selected Achievements callout (left-bar, no fill — print-robust), Professional Experience with absolute-positioned tabular-num dates. Page footer `Sean Ivins page X of Y`. Single `--accent` token swaps the entire palette.
- Layout chose `position: relative` + `absolute` dates over `display: table` because the latter caused multi-page bullet/header fragmentation in WeasyPrint.
- Photo support: drop a JPG at `data/photos/<file>.jpg`, set `PROFILE['photo_path']`. Path validated under `data/` before file:// exposure.
- Internal `resume_template.html`: yellow `INTERNAL TRACKING — NOT FOR SUBMISSION` banner so misrouted PDFs are unmistakable. Render gated on `is_internal=True` flag from `render_pdf` when `--recruiter` omitted.
- `data/photos/.gitkeep` + `.gitignore` allowlist (photos are user PII).
- Reference render: 2-page Filevine SE resume (cleaner than the 3-page rendercv `classic.designed` reference Sean was using as a baseline).

**Files touched (24):** config.py · CLAUDE.md · .gitignore · requirements.txt · careerops/{__init__,pipeline,paths(new)}.py · data/{resume_template,resume_template_recruiter,resumes/base}.* · data/photos/.gitkeep · modes/{_shared,cover-letter}.md · scripts/{start.sh,discover,render_pdf,save_resume,update_role,print_role,track_outreach,import_linkedin_connections}.py · scripts/migrations/{__init__,m001..m004}.py.

**Decisions:**
- Render-template layout: `position:absolute` dates beat `display:table-cell` headers because WeasyPrint fragments table-cell content across pages unpredictably (bullets appeared under the WRONG header on page 3 in early iterations).
- DB persistence: user-data dir > git-attribute store > symlink. The user-data dir is the only option that survives `git worktree remove` AND `rm -rf coin/` AND machine moves with cloud-synced Library folders.
- Migration ID compat: rather than rename existing schema_migrations rows, m001's `_already_applied` accepts both the old `001_…` and the new `m001_…` IDs. Avoids destructive DB rewrites at upgrade.

---

## What Was Just Done (2026-04-25, Session 5 — Deferred-followup batch 2)

### COIN-NETWORK-LIVE-SCRAPE + COIN-OFERTAS-LEVELS-FYI + COIN-COVER-RECIPIENT-FROM-NETWORK ✅ COMPLETE

**Tests:** 193 → **223 passing** (+30; 0 regressions). Verdict: PASS.

**1. COIN-NETWORK-LIVE-SCRAPE** — wire the LinkedIn search-page fallback
- `careerops/network_scrape.py` — `parse_linkedin_people_search(html, target_company)` (BeautifulSoup parser tolerant of LinkedIn's class-name churn, dedupes by URL, strips connection-degree suffixes "• 2nd", normalizes relative `/in/<slug>` to absolute https) + `upsert_scraped(rows, db_path)` (parameterized UPSERT with COALESCE preserving more-specific company strings from prior CSV imports)
- `tests/fixtures/network/sample_search_page.html` — 5-card fixture covering valid cards, malformed cards (no profile URL, parser must skip), duplicate URLs (parser must dedupe), relative-vs-absolute href forms, connection-degree suffix stripping
- `tests/test_network_scrape.py` (10 tests) — parser unit tests + upsert idempotency + the COALESCE-preserves-export-company contract test
- `modes/network-scan.md` Step 3 rewritten: explicit browser MCP invocation (`Claude_in_Chrome` preferred, `Claude_Preview` fallback), HTML capture to `/tmp/linkedin_search.html` (not into project tree because LinkedIn HTML carries incidental sidebar PII), `parse_linkedin_people_search` → `upsert_scraped` pipeline, graceful degradation when LinkedIn re-skins the search HTML
- No live LinkedIn auth scripted from Python (Sean's browser session belongs to him; Coin only consumes the rendered HTML he can already see)

**2. COIN-OFERTAS-LEVELS-FYI** — market-comp anchor when only one real offer exists
- `careerops.pipeline.insert_market_anchor(company, title, base_salary, *, rsu_total_value=0, ...)` — wraps `insert_offer` with `status='market_anchor'` so synthetic comps stay out of `list_offers(status='active')` (the Y1-best ranking in ofertas Step 3 stays clean) but join the comparison via `combined = list_offers(active) + list_market_anchors()`
- `careerops.pipeline.list_market_anchors()`
- `tests/test_market_anchor.py` (4 tests) — happy path, status segregation from active offers, required-field validation, combined-list pattern
- `modes/ofertas.md` adds Step 5.5 — when 1 active offer + 0 anchors, prompt Sean to look up the same role/level on Levels.fyi and capture the P50 base + RSU + bonus; counter-brief then cites "Levels.fyi P50 for &lt;company&gt; &lt;title&gt;" instead of bluffing a competing offer. Skip path emits a soft counter ("Below market based on independent research") that still refuses to fabricate

**3. COIN-COVER-RECIPIENT-FROM-NETWORK** — cover-letter recipient_name auto-population
- `scripts/migrations/m004_outreach_role_tag.py` — adds `outreach.contact_role TEXT` + `outreach.target_role_id INTEGER` + `idx_outreach_contact_role`. Idempotent (PRAGMA-checked column adds, applied flag in schema_migrations). Self-bootstraps m003 inline if applied to a fresh DB
- `careerops.pipeline.tag_outreach_role(outreach_id, contact_role, target_role_id=None)` — validates against `VALID_CONTACT_ROLES = ('hiring_manager', 'team_member', 'recruiter', 'exec_sponsor', 'alumni_intro')`
- `careerops.pipeline.find_hiring_manager_for_role(role_id)` — joins `outreach × connections` filtered to `contact_role='hiring_manager'`; checks both `role_id` and `target_role_id` columns so the same contact can be tagged for a different role; returns most-recently-drafted match; tolerates missing tables / missing column on fresh DBs (returns None instead of raising)
- `tests/test_hiring_manager_lookup.py` (11 tests) — m004 schema + idempotency + m003-bootstrap, tag validation, recursive lookup paths, ignores non-hiring-manager tags, picks most-recent on multi-tag, missing-schema graceful return, target_role_id branch
- `modes/network-scan.md` Step 6.5 — optional hiring-manager tagging prompt after the brief; instructs the agent to call `tag_outreach_role` with the right enum value; documents all 5 valid contact roles
- `modes/cover-letter.md` Step 1 — auto-lookup via `find_hiring_manager_for_role(<role_id>)`; `recipient_name = hm['full_name']` when present, null when not; explicit refusal to invent a hiring manager
- `modes/_shared.md` adds a new "Cross-mode helpers" section enumerating all the helpers + valid `contact_role` values (so future modes don't grep around)

**Schema migrations applied to live DB:** m003 (already), m004 (this session). 002 + 003 + 004 all tracked in `schema_migrations`.

**New tests (30):**
- `test_network_scrape.py` (10): parser dedupe, malformed-card skip, URL normalization, tracking-param strip, target_company propagation, seniority classification, empty-HTML handling, fresh-DB schema bootstrap, upsert idempotency, COALESCE preserves CSV-export company over scraper target
- `test_market_anchor.py` (4): happy path, status segregation, required-field validation, combined-list pattern
- `test_hiring_manager_lookup.py` (11): m004 schema/idempotency/bootstrap, tag validation, lookup paths
- `test_cover_letter_mode.py` extended (1): recipient_name lookup documented + anti-fabrication guard
- `test_network_scan_mode.py` extended (2): live-scrape pipeline documented + hiring-manager tagging documented with all 5 valid roles
- `test_ofertas_mode.py` extended (2): Step 5.5 documented + market-anchor truthfulness gate

**Files touched:** 13 (4 mode .md, _shared.md, 1 new careerops module, 1 pipeline.py extension, 1 new migration, 1 new HTML fixture, 4 new test files + 3 extended test files, this state doc).

**Decisions:**
- Live-scrape stays parser-only (no Python-driven LinkedIn auth) — keeps Sean's session uncompromised and avoids TOS exposure on auth-script paths.
- Market anchors live in the same `offers` table with `status='market_anchor'` instead of a separate table — same math (`year_one_tc`, `three_year_tc`) applies, ofertas comparison code stays trivial.
- Hiring-manager tagging on `outreach` rather than a new table — `outreach` already has the role↔connection link; one column add is cleaner than a junction table.

---

## What Was Just Done (2026-04-25, Session 5 — Code-review --fix EVERYTHING)

### All review findings resolved (CRITICAL → HIGH → MEDIUM → LOW + pre-existing) ✅ COMPLETE

**Tests:** 170 → **193 passing** (23 net new, 0 regressions). Verdict: PASS.

**HIGH (6) — all fixed:**
- `import_linkedin_connections.py` rows_inserted/rows_updated counter — replaced ON-CONFLICT-rowcount-hack with explicit pre-SELECT existence check; per-row insert/update accounting now accurate (test: `test_inserted_vs_updated_counts_are_accurate`)
- `offer_math.py` STATE_TAX_RATES + ANNUAL_BASE_BUMP + DEFAULT_VEST_SCHEDULE moved to `config.py`; offer_math now imports them
- `import_linkedin_connections.py` DEFAULT_CSV reads `config.LINKEDIN_CONNECTIONS_CSV`
- `cover-letter.md` Greenhouse field 5 → 6 (was wrong; field 5 is Resume); Lever 7 → 10 (was wrong; field 7 is Current company)
- `network-scan.md` `/coin track-outreach` reference now backed by a real `scripts/track_outreach.py` helper (8 tests in `test_track_outreach.py`); SKILL.md routes `track-outreach <id> sent|replied [--note]` and `track-outreach --list`

**MEDIUM (9) — all fixed:**
- `three_year_tc` Y2/Y3 RSU growth exponents: was `**2` / `**3` (one year too many on each); now `**1` / `**2` so Y2 vest sits 1 year past grant FMV and Y3 sits 2 years past. Test `test_three_year_tc_y3_growth_uses_squared_exponent` locks in the math (Y3 @ +10% = 25k × 1.21 = 30,250 exactly)
- `vest_curve` ZeroDivisionError when `rsu_vest_years=0` — `_safe_vest_years` helper coerces to default 4. Test `test_zero_vest_years_does_not_crash`
- `connections` + `outreach` schema now in `scripts/migrations/m003_connections_outreach.py`; importer keeps `ensure_schema()` for fresh-DB compat. 3 tests in `test_migrations_m003.py`
- Migrations renamed: `001_archetypes_5_to_4.py` → `m001_…`, `002_offers_table.py` → `m002_…`, plus new `m003_…`. All importable as Python modules now. Test loader updated.
- `render_pdf.py` + `render_cover_letter.py` `base_url` anchored to `ROOT` (script's project) instead of `Path.cwd()` — invariant under shell cwd, fixes a parity defect that was pre-existing in `render_pdf.py` since session 3
- `render_cover_letter.py` `--out` and `--input` constrained to `data/resumes/generated/` via `_validate_under_generated`; refuses path traversal
- `onboarding.md` question-count: header / steps / summary now consistently say 7 (was 9 / 7 / 8); SKILL.md Onboarding section follows. Test `test_question_count_consistent`
- SKILL.md Discovery menu adds `/coin setup` and `/coin track-outreach <id>`
- `import_linkedin_connections.py::import_csv` now mkdir-s the DB parent inside the function (not just in `main()`) — works when called from tests / non-CLI

**LOW (13) — all fixed:**
- `render_cover_letter.py` defers Jinja2 + WeasyPrint imports into `_build_env()` / `render()` so the no-op CLI path is fast; prints `Selected cover JSON: <path>` so Sean sees which lane was picked
- `pipeline.insert_offer` raises `ValueError` listing missing required keys instead of low-context `IntegrityError`. Bonus fix discovered: also stops emitting NULL for unset columns so DDL DEFAULTs (status='active', signing_bonus=0, etc.) actually apply. Test `test_insert_offer_writes_row` + `test_insert_offer_missing_required_raises`
- `vest_curve` strips per-element whitespace ("25 / 25 / 25 / 25" parses identically to "25/25/25/25"). Test `test_whitespace_in_schedule_parses`
- `delta_table` returns a proper `TypedDict(DeltaRow)` shape. Test `test_delta_table_returns_typed_dict_shape`
- `m002_offers_table.main()` consolidated through `apply()` so connection lifecycle is guarded by try/finally on every path
- `import_linkedin_connections.py::main` validates `--db` is under `data/db/` (rejects writes outside the project)
- `network-scan.md` Step 2 + Step 7 SQL examples gain "NEVER f-string into SQL" comments + use parameterized `?` bindings explicitly
- `network-scan.md` Step 5 clarifies that `seniority='recruiter'` is a *scan-time* concept — the import classifier emits leadership/senior_ic/peer only; recruiter override is title-pattern matching at scan time
- `network-scan.md` refusal table gains: "Citing a metric not in PROFILE.positions in any draft DM" — parity with cover-letter.md
- `onboarding.md` raw resume now staged via `tempfile.mkstemp` and unlinked after Step 9 success (PII off disk once profile is written)
- `onboarding.md` Step 7 surfaces $160K/$200K Sean default + warns on lower fat-finger
- `cover-letter.md` audit subset now uses audit.md's exact check labels (Check 1 Education / 2 Pedigree / 3 Cox attribution / 4 Vague-flex / 5 Metric provenance) — drops the "verb authenticity" mismatch that wasn't a numbered check
- `ofertas.md` adds explicit Step 0 "Load the AskUserQuestion tool" (mirrors onboarding); Step 2 references the load instead of conditional
- `auto-pipeline.md` lane list now reads from `config.LANES.keys()` instead of hardcoded literal; `update_lane()` and `update_role_notes()` helpers are now invoked instead of raw SQL (TODOs were stale — helpers exist)
- `cover_letter_template.html` recipient block: `{% if recipient_name %}{{ recipient_name }}{% else %}Hiring Team — {{ company }}{% endif %}` (was double-printing both)
- `config.py` adds `ONBOARDING_MARKER`, `ONBOARDING_DIR`, `ONBOARDING_RAW_RESUME`, `LINKEDIN_CONNECTIONS_CSV`, `NETWORK_DATA_DIR` constants — all path duplications now route through one source

**PRE-EXISTING (2) — also fixed:**
- `CLAUDE.md` refreshed: 5 archetypes → 4 (with Removed-lanes note); comp floor `$180K base / $250K total` → `$160K base / $200K total`; new Rule #7 codifies the truthfulness gates from `_shared.md` Operating Principle #3; date stamp 2026-04-24 → 2026-04-25
- `render_pdf.py` `base_url` defect (cwd-dependent) fixed at the same time as `render_cover_letter.py` for parity

**New tests added (23):**
- `test_track_outreach.py` (8): update sent/replied paths, note attachment, invalid action, unknown id, list_open semantics, role filter, missing-table error
- `test_migrations_m003.py` (3): tables created, idempotency, indexes
- `test_pipeline_offers.py` (3): insert_offer happy path, missing-keys ValueError, list_offers default-active filter
- `test_offer_math.py` extended (5): Y3 growth squared exponent locked in, STATE_TAX_RATES from config, zero-vest crash guard, whitespace parsing, TypedDict shape
- `test_import_linkedin_connections.py` extended (3): accurate inserted/updated split on re-import, parent-dir mkdir, DEFAULT_CSV from config
- `test_cover_letter_mode.py` updated (1): audit subset uses audit.md's actual check labels
- `test_ofertas_mode.py` updated (no count change): m002 import via package path, not file path

**Files touched:** 26 (4 mode files, SKILL.md, CLAUDE.md, 4 careerops/scripts files, 3 migration files, 1 template, 13 test files including 3 new). One commit per logical group below.

---

## What Was Just Done (2026-04-25, Session 5 — Follow-up batch)

### All four deferred follow-ups landed in one session ✅ COMPLETE

**Tests:** 98 → **170 passing** (72 net new, 0 regressions).

**1. COIN-OFERTAS — multi-offer comparison + negotiation brief** (santifer port)
- `modes/ofertas.md` (7-step decision-support flow with 5 hard refusals;
  "Coin does NOT recommend a specific offer" — surfaces math + trade-offs only)
- `careerops/offer_math.py` — pure functions: `vest_share_y1`, `vest_curve`,
  `year_one_tc`, `three_year_tc` with ±growth sensitivity, `historical_hit_rate`,
  `state_tax_rate` (top-marginal approximation), `delta_table`
- `scripts/migrations/002_offers_table.py` (idempotent, tracked)
- `careerops.pipeline.insert_offer` + `list_offers` helpers
- 24 new tests (offer math + mode structure + migration smoke)

**2. COIN-COVER-LETTER — separate cover letter generation** (proficiently port)
- `modes/cover-letter.md` (7-step flow; 280-word hard cap; story-parity +
  JD-keyword-parity checks against tailored resume; reuses audit checks 1-5
  for truthfulness — skips orthogonality/lane checks; 7 hard refusals)
- `scripts/render_cover_letter.py` — refuses on `audit_passes != true`,
  Jinja autoescape on, base_url scoped to `data/` (security parity with
  render_pdf.py)
- `data/cover_letter_template.html` (single-page Letter, Georgia serif)
- `config.COVER_TEMPLATE_PATH`
- Auto-pipeline integration (Step 6): cover-letter is additive — resume
  still ships if cover audit fails
- Apply mode integration: Greenhouse field 6 + Lever field 10 wire the
  cover artifact (cover.pdf for upload, paragraphs.hook for textarea)
- 13 new tests

**3. COIN-NETWORK-SCAN — LinkedIn warm-intro discovery** (proficiently port)
- `modes/network-scan.md` (7-step discovery+drafting flow; 6 hard refusals;
  warmth = 40% recency + 35% seniority + 25% relevance; recruiter override
  scores 90; truthfulness gate via `_shared.md` Operating Principle #3)
- `.claude/skills/coin/references/network-patterns.md` — CSV schema,
  recency tiers, seniority classifier, relevance signals, 4 outreach
  templates by recency tier (hot/warm/cold/recruiter), forbidden behaviors
- `scripts/import_linkedin_connections.py` — idempotent CSV ingest from
  LinkedIn's "Get a copy of your data" export; creates `connections` +
  `outreach` tables; company normalization collapses Inc./LLC/punctuation
  variants; preamble-tolerant CSV reader for LinkedIn's variable header
- 17 new tests (mode structure + reference content + schema + idempotency
  + company normalization + dry-run)
- Coin does NOT auto-send DMs and does NOT scrape with logged-in cookies

**4. COIN-ONBOARDING-EXECUTABLE — convert SKILL.md prose to executable mode**
  (job-scout pattern)
- `modes/onboarding.md` (9 deterministic AskUserQuestion blocks; Step 0
  loads AskUserQuestion via ToolSearch; Step 1 safety gate for existing
  profile with Re-onboard / Update specific fields / Cancel branches;
  Step 8 pedigree-constraint question explicitly load-bearing; Step 9
  atomic write via staging file + yaml.safe_load round-trip; identity
  slice only — never touches positions/education/skills_grid)
- SKILL.md: deleted the 9-step prose Onboarding section; replaced with
  pointer at modes/onboarding.md; routing table adds
  `setup`/`onboard`/`re-onboard`; First-Run Setup Checklist now dispatches
  onboarding between init-DB and smoke-test
- 18 new tests including SKILL.md regression (deleted prose markers must
  not reappear; First-Run Checklist must dispatch onboarding)
- 5 hard refusals (no silent overwrite, no inferred pedigree, identity-slice
  only, no question-skipping, no >5 smoke discovery)

**Cross-cutting infrastructure:**
- `.gitignore`: added `data/network/`, `data/onboarding/`
- `_shared.md` mode catalog: 4 new rows (ofertas, cover-letter,
  network-scan, onboarding)
- SKILL.md: 4 new routing entries + 3 new Discovery menu lines
- `scripts/migrations/__init__.py` for importable migration package

**Open follow-ups (after this batch — none from the original four):**
- ~~COIN-NETWORK-LIVE-SCRAPE~~ ✅ landed in Session 5 batch 2
- ~~COIN-OFERTAS-LEVELS-FYI~~ ✅ landed in Session 5 batch 2
- ~~COIN-COVER-RECIPIENT-FROM-NETWORK~~ ✅ landed in Session 5 batch 2

---

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
- ~~COIN-NETWORK-SCAN~~ ✅ landed in Session 5
- ~~COIN-OFERTAS~~ ✅ landed in Session 5
- ~~COIN-COVER-LETTER~~ ✅ landed in Session 5
- ~~COIN-AUTO-PIPELINE-EXECUTABLE / COIN-ONBOARDING-EXECUTABLE~~ ✅ landed in Session 5

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

1. **Filevine SE (id 137) — submit.** The new-template render lives at
   `data/resumes/generated/0137_enterprise-sales-engineer_2026-04-24_recruiter.pdf`
   and is great. Drop a headshot at `coin/data/photos/sean.jpg`, set
   `PROFILE['photo_path'] = 'photos/sean.jpg'` in `data/resumes/base.py`,
   re-render with `/coin pdf 137 --recruiter`, then submit and
   `/coin track 137 applied`.
2. **Discover next batch** — `/coin discover` (now Utah+Remote default,
   consultancies filtered) to refresh the pipeline. Score new arrivals.
3. **Re-score all existing roles** under the 8-dimension weights — wire
   `--rescore-existing` flag on `discover.py` (still not implemented).
4. **Levels.fyi comp extraction** — Phase 2 backlog; most roles still
   have null `comp_min`.
5. **Optional polish (LOW from Session 6, deferred):**
   - Bundle Inter woff2 under `data/fonts/` for Reactive-Resume parity
     typography (currently fall back to Helvetica Neue/Arial).
   - Extract `careerops/dashboard.py` from `pipeline.py` (presentation vs
     CRUD separation — flagged LOW by architecture review).
   - Resolve `sean@lifestory.co` vs `sivins@caengineering.com` canonical
     outbound email (COIN-EMAIL-CANONICAL — tracked in _shared.md).

**Closed (do not re-open):** Netflix TPM Infrastructure (id 4) — Session 3
tailor under the legacy `cox-style-tpm` lane; output was stale and the
underlying lane was renamed by m001. Artifacts deleted; row marked
`closed` with note. Re-tailor from scratch under `mid-market-tpm` if Sean
revisits.

## Active Blockers

None. No API key needed. DB persistent across worktrees.

---

## Roadmap

| Task | Description | Status |
|------|-------------|--------|
| S-1.1 | Scraper: LinkedIn + Indeed live results | ✅ Done (LinkedIn live; Indeed Cloudflare-degraded as expected) |
| S-1.2 | Analyzer: JD parsing via Claude | ✅ Done (moved to `modes/score.md` — session-native) |
| S-1.3 | Transformer: lane-aware resume rewriting | ✅ Done (moved to `modes/tailor.md`) |
| S-1.4 | Pipeline DB: CRUD + dashboard | ✅ Done (11-state machine + Rich dashboard) |
| S-1.5 | Compensation: Levels.fyi cross-reference | 🚧 Pending — Phase 2 |
| S-2.1 | Resume quality: PDF via weasyprint | ✅ Done (Session 6 — Reactive-Resume sidebar template + photo support, beats rendercv reference) |
| S-2.2 | Glassdoor comp band scraping | 🔲 Backlog |
| S-2.3 | Full cover letter generation (beyond hook) | 🔲 Backlog |
| S-2.4 | Batch resumability per santifer (claude -p workers) | 🔲 Backlog |
| S-3.1 | Scheduler: daily auto-search cron | 🔲 Backlog |
| S-3.2 | Multi-board: Greenhouse / Lever / Workday | 🔲 Backlog |

---

## Resolved Bugs

- (2026-04-26) Quarantine resurrection: `upsert_role` ON CONFLICT and `update_lane`
  only sank fit_score=0 for the literal `'out_of_band'` lane. Legacy ids
  (`cox-style-tpm`, etc.) bypassed the sink and resurrected stale scores even
  though `score_breakdown` returned 0 for any lane not in LANES. Fixed by
  broadening the predicate to `lane == 'out_of_band' OR lane NOT IN <current 4>`.
- (2026-04-26) `roles` table COALESCE didn't preserve more-specific company
  strings on conflict (matches `network_scrape.upsert_scraped` contract). Now
  wraps each text field with `NULLIF(excluded.x, '')`.
- (2026-04-26) `cover-letter.md` Check 2 was mislabeled — used Check 4's
  vague-flex content under the Pedigree non-claim label, leaving the actual
  pedigree-employment check unrun on cover letters.
- (2026-04-26) Path traversal: `render_pdf.py`, `save_resume.py`,
  `update_role.py`, `import_linkedin_connections.py` accepted any filesystem
  path. Centralised guard in `careerops/paths.py`.
- (2026-04-26) PDF template multi-page fragmentation: `display: table` on
  `.position-head` caused bullets to render under the WRONG header on page 3+
  in WeasyPrint. Switched to `position: absolute` for dates.
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
