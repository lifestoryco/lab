#!/bin/bash
# Coin session start — health check
#
# Worktree-aware: when invoked without an explicit dir, prefer the project's
# `coin/` subtree under the active git worktree over $PWD. This keeps the
# script honest when the user runs from `lab/`, `lab/coin/`, or any worktree
# under `.claude/worktrees/<name>/coin/`.

if [ -n "$1" ]; then
  PROJECT_DIR="$1"
elif command -v git >/dev/null 2>&1; then
  TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -n "$TOPLEVEL" ] && [ -d "$TOPLEVEL/coin" ]; then
    PROJECT_DIR="$TOPLEVEL/coin"
  else
    PROJECT_DIR="${TOPLEVEL:-$PWD}"
  fi
else
  PROJECT_DIR="$PWD"
fi

cd "$PROJECT_DIR" || exit 1

echo "═══════════════════════════════════════════════"
echo "  Coin | Branch: $(git branch --show-current 2>/dev/null || echo 'detached')"
echo "  HEAD: $(git rev-parse --short HEAD 2>/dev/null || echo 'no commits')"
echo "═══════════════════════════════════════════════"

PASS=true

# Python version
PY_VERSION=$(python3 --version 2>&1)
if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
  echo "  Python:   ✅ $PY_VERSION"
else
  echo "  Python:   ❌ $PY_VERSION (requires 3.11+)"
  PASS=false
fi

# Virtual environment
if [ -d ".venv" ]; then
  echo "  Venv:     ✅ .venv/"
else
  echo "  Venv:     ❌ missing — create with: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  PASS=false
fi

# Core dependencies (httpx, bs4, rich, yaml) — anthropic is intentionally absent
if .venv/bin/python -c "import httpx, bs4, rich, yaml" 2>/dev/null; then
  echo "  Packages: ✅ (httpx, bs4, rich, yaml)"
else
  echo "  Packages: ❌ run: .venv/bin/pip install -r requirements.txt"
  PASS=false
fi

# Coin runs inside Claude Code subscription — no API key required.
# Check that no Anthropic SDK is installed (confuses users if it is).
if .venv/bin/python -c "import anthropic" 2>/dev/null; then
  echo "  API key:  ⚠️  anthropic SDK installed — Coin does not need it (safe to ignore)"
else
  echo "  API key:  ✅ no anthropic SDK — runs inside Claude Code session"
fi

# .env file (optional — only used to override defaults like comp floors)
if [ -f ".env" ]; then
  echo "  Env:      ✅ .env found (overrides active)"
else
  echo "  Env:      ℹ️  no .env — using defaults from .env.example (OK for most users)"
fi

# Pipeline DB — resolved via config.py (persistent across worktrees by default;
# user-data dir on macOS/Linux, %APPDATA% on Windows). Override: COIN_DB_PATH.
DB_INFO=$(.venv/bin/python -c "from config import DB_PATH; from pathlib import Path; from careerops.pipeline import summary; p=Path(DB_PATH); print(p, summary().get('total', 0) if p.exists() else 'init')" 2>/dev/null)
if [ -n "$DB_INFO" ]; then
  DB_PATH_RESOLVED=$(echo "$DB_INFO" | awk '{print $1}')
  COUNT=$(echo "$DB_INFO" | awk '{print $2}')
  if [ "$COUNT" = "init" ]; then
    echo "  DB:       ⚠️  not initialized at $DB_PATH_RESOLVED — auto-creates on first /coin run"
  else
    echo "  DB:       ✅ $DB_PATH_RESOLVED ($COUNT roles tracked)"
  fi
else
  echo "  DB:       ⚠️  cannot resolve (config import failed)"
fi

echo "═══════════════════════════════════════════════"

if [ "$PASS" = false ]; then
  echo "  ❌ Environment has issues — fix before starting work"
  exit 1
else
  echo "  ✅ Environment healthy — ready for /coin"
fi
