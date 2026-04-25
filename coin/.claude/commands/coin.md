---
description: Coin career-ops engine — modal router. Paste a JD/URL → full pipeline. Or pass a sub-command. discover, status, tailor, audit, pdf, track, apply, followup, patterns, interview-prep, score, liveness, setup, help.
---

# /coin {input}

Invoke the Coin skill with the user's input (or no input to start at the discovery menu).

The skill router lives at `.claude/skills/coin/SKILL.md`. Load it and dispatch to the correct mode file under `modes/` based on `{input}`.

## Modes (current — 2026-04-25)

**Auto-pipeline (the killer mode):**
- **Pasted JD text or URL** with no other directive → `modes/auto-pipeline.md` runs ingest → score → audit → tailor → render → report end-to-end. Stops only at the `applied` gate.

**User commands:**
| Input | Mode |
|---|---|
| (no input) | discovery menu |
| `discover` (optionally `--utah`, `--lane <name>`, `--limit N`) | `modes/discover.md` |
| `<URL>` | `modes/url.md` (or auto-pipeline if no other context) |
| `score <id>` | `modes/score.md` |
| `tailor <id>` | `modes/tailor.md` |
| `audit <id>` | `modes/audit.md` (9 truthfulness checks) |
| `pdf <id> [--recruiter\|--brief]` | `scripts/render_pdf.py` |
| `track <id> <status> [note]` | `modes/track.md` |
| `apply <id>` | `modes/apply.md` (browser-assisted ATS form fill) |
| `status` / `dashboard` | `modes/status.md` |
| `followup` | `modes/followup.md` (cadence tracker) |
| `patterns` | `modes/patterns.md` (rejection cluster analysis) |
| `interview-prep <id>` | `modes/interview-prep.md` |
| `liveness` | `scripts/liveness_check.py` |
| `setup` | first-run setup checklist (in SKILL.md) |
| `help` | print this routing table |

## Order of operations every session

1. Always read `modes/_shared.md` first (canonical lanes, comp floor, truthfulness gates, scoring config).
2. Then read the dispatched mode file.
3. Run all Python via `.venv/bin/python` from `/Users/tealizard/Documents/lab/coin/`.

## Lanes (4 — current)

`mid-market-tpm` · `enterprise-sales-engineer` · `iot-solutions-architect` · `revenue-ops-operator`

(Old lanes `cox-style-tpm`, `titanx-style-pm`, `global-eng-orchestrator`, `revenue-ops-transformation` were retired in Session 4 — see _shared.md "What changed in this refresh".)

## Comp floor

$160K base / $200K total. Set in `config.py` (`COIN_MIN_BASE` / `COIN_MIN_TC` env overrides).

## Hard rules (from SKILL.md)

1. **Accuracy** — never fabricate, inflate, or invent metrics.
2. **User corrections override.**
3. **Workflow steps as written.**
4. **Truthfulness gates** — Cox/TitanX/Safeguard need "as Hydrant's <role>" framing; no Fortune-500 / seven-figure puffery; no claimed CS degree.
5. **Human gate** for `applied` / `interview` / `offer` transitions.
