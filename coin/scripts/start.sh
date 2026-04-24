#!/bin/bash
# Coin session start — health check

PROJECT_DIR="${1:-$PWD}"
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

# Pipeline DB
if [ -f "data/db/pipeline.db" ]; then
  COUNT=$(.venv/bin/python -c "from careerops.pipeline import summary; print(summary().get('total', 0))" 2>/dev/null)
  echo "  DB:       ✅ pipeline.db ($COUNT roles tracked)"
else
  echo "  DB:       ⚠️  not initialized — will auto-create on first /coin run"
fi

echo "═══════════════════════════════════════════════"

if [ "$PASS" = false ]; then
  echo "  ❌ Environment has issues — fix before starting work"
  exit 1
else
  echo "  ✅ Environment healthy — ready for /coin"
fi
