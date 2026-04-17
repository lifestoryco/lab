#!/usr/bin/env bash
# Holo session health check. Called by /start-session.
# Usage: bash scripts/start.sh "$PWD"
set -e

PROJECT_DIR="${1:-$PWD}"
cd "$PROJECT_DIR"

BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
BASE=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
ENV_OK=true

echo "  Branch: $BRANCH"
echo "  HEAD:   $BASE"
echo ""

# ── venv ────────────────────────────────────────────────────────────────────
if [ -f ".venv/bin/python" ]; then
  echo "  ✅ venv"
else
  echo "  ❌ venv missing — run /holo-setup first"
  ENV_OK=false
fi

# ── dependencies ─────────────────────────────────────────────────────────────
if [ "$ENV_OK" = true ]; then
  if .venv/bin/python -c "import pandas, numpy, requests, bs4, dateutil" 2>/dev/null; then
    echo "  ✅ dependencies"
  else
    echo "  ❌ missing packages — run: .venv/bin/pip install -r requirements.txt"
    ENV_OK=false
  fi
fi

# ── config ───────────────────────────────────────────────────────────────────
if [ -f "config.py" ]; then
  echo "  ✅ config.py"
else
  echo "  ❌ config.py missing"
  ENV_OK=false
fi

# ── test suite quick check ───────────────────────────────────────────────────
if [ -d "tests" ]; then
  TEST_COUNT=$(find tests -name "test_*.py" | wc -l | tr -d ' ')
  echo "  ✅ tests/ ($TEST_COUNT test files)"
fi

echo ""

if [ "$ENV_OK" = false ]; then
  echo "❌ Environment has issues — fix above before starting work."
  exit 1
fi

echo "  Env: ✅"
