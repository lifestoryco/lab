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
  echo "  Venv:     ❌ missing — run /coin-setup"
  PASS=false
fi

# Dependencies
if [ -f ".venv/lib/python3.11/site-packages/anthropic/__init__.py" ] || \
   .venv/bin/python -c "import anthropic" 2>/dev/null; then
  echo "  Packages: ✅"
else
  echo "  Packages: ❌ run: .venv/bin/pip install -r requirements.txt"
  PASS=false
fi

# .env file
if [ -f ".env" ]; then
  echo "  Env:      ✅ .env found"
else
  echo "  Env:      ❌ missing .env — copy .env.example and fill in ANTHROPIC_API_KEY"
  PASS=false
fi

# Pipeline DB
if [ -f "data/db/pipeline.db" ]; then
  echo "  DB:       ✅ pipeline.db"
else
  echo "  DB:       ⚠️  not initialized — run /coin-setup"
fi

echo "═══════════════════════════════════════════════"

if [ "$PASS" = false ]; then
  echo "  ❌ Environment has issues — fix before starting work"
  exit 1
else
  echo "  ✅ Environment healthy"
fi
