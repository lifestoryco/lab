# Coin

Agentic career ops engine for Sean Ivins. Hunts high-compensation roles across TPM, PM, and Technical Sales Engineering, then dynamically rewrites his resume to match each target lane.

## Setup

```bash
claude  # opens Claude Code
/coin-setup
```

## Commands

| Command | What it does |
|---------|-------------|
| `/coin-setup` | First-time installer |
| `/coin-search tpm-high` | Search for roles by lane |
| `/coin-apply 42` | Generate tailored resume for pipeline role #42 |
| `/coin-track` | View and update the application pipeline |
| `/coin [question]` | Plain-English interface |
| `/start-session` | Session health check + brief |
| `/end-session` | Commit, update state, push |
| `/sync` | Rebase onto origin/main |
| `/code-review` | 4-agent parallel code review |
| `/alpha-squad [topic]` | 7-member advisory board |
| `/prompt-builder S-X.Y` | Build a task prompt from the roadmap |
| `/run-task S-X.Y` | Execute a pending task prompt |

## Target Lanes

| Lane | Label |
|------|-------|
| `tpm-high` | High-Tier Technical Program Manager |
| `pm-ai` | AI Product Manager |
| `sales-ent` | Enterprise Technical Sales Engineer |

## Comp Filter

Minimum $180K base. Override with `--override-comp` flag.
