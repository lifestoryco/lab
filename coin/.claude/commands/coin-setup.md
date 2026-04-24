---
description: First-time setup for Coin. Creates the virtual environment, installs dependencies, initializes the SQLite pipeline DB, and verifies the Anthropic API key. Run once on fresh clone.
---

# /coin-setup

First-time installer. Run once per machine.

---

## Step 1 — Check Python version

```bash
python3 --version
```

Requires Python 3.11+. If older: `❌ Upgrade Python to 3.11+`

---

## Step 2 — Create virtual environment

```bash
python3 -m venv .venv
```

---

## Step 3 — Install dependencies

```bash
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

If any package fails, report the exact error and stop.

---

## Step 4 — Set up environment file

```bash
ls .env
```

If `.env` does not exist:
```bash
cp .env.example .env
```
Then tell the user: `⚠️ Fill in ANTHROPIC_API_KEY in .env before continuing`
Wait for confirmation before proceeding.

---

## Step 5 — Initialize the pipeline database

```bash
.venv/bin/python -c "from careerops.pipeline import init_db; init_db(); print('DB initialized')"
```

---

## Step 6 — Verify Anthropic API connectivity

```bash
.venv/bin/python -c "
import os, anthropic
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic()
msg = client.messages.create(model='claude-haiku-4-5-20251001', max_tokens=10, messages=[{'role':'user','content':'ping'}])
print('API OK —', msg.content[0].text)
"
```

---

## Step 7 — Report

```
═══════════════════════════════════════════════
  Coin Setup Complete
═══════════════════════════════════════════════
  Python:   ✅ {version}
  Venv:     ✅ .venv/
  Packages: ✅ installed
  DB:       ✅ data/db/pipeline.db
  API:      ✅ Anthropic connected

  Run /start-session to begin.
```

If any step fails, stop and report — do not continue to the next step.
