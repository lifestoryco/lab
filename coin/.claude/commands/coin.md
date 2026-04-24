---
description: Coin career ops — modal router. No args = discover new roles. Or pass a URL, `tailor <id>`, `track <id> <status>`, `status`, `score <id>`.
---

# /coin {input}

Invoke the Coin skill with the given input (or no input to start discovery).

The skill router lives at `.claude/skills/coin/SKILL.md`. Load it and
dispatch to the correct mode file under `modes/` based on `{input}`.

Modes:
- **(no input)** → discover new roles across all 5 archetypes
- **`<URL>`** → ingest and score one role
- **`score <id>`** → fetch + parse JD for role
- **`tailor <id>`** → generate lane-tailored resume JSON
- **`track <id> <status>`** → transition pipeline state
- **`status`** → Rich dashboard

Always read `modes/_shared.md` first, then the selected mode.
Run all Python via `.venv/bin/python` from the coin/ directory.
