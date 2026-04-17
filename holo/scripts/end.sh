#!/usr/bin/env bash
# Holo session close script. Called by /end-session.
# Usage: bash scripts/end.sh "$PWD"
set -e

PROJECT_DIR="${1:-$PWD}"
cd "$PROJECT_DIR"

echo "🔍 Validating clean close..."
echo ""

# ── uncommitted changes (scoped to holo/ only) ───────────────────────────────
# Use -- . to check only files under the current project directory,
# ignoring unrelated changes at the repo root.
DIRTY=$(git status --porcelain -- . 2>/dev/null)
if [ -n "$DIRTY" ]; then
  echo "  ⚠️  Uncommitted changes in holo/:"
  git status --short -- .
  echo ""
  echo "  Stage and commit before calling end-session."
  exit 1
fi
echo "  ✅ Working tree clean"

# ── commits ahead of origin ───────────────────────────────────────────────────
AHEAD=$(git rev-list origin/main..HEAD --count 2>/dev/null || echo "0")

if [ "$AHEAD" -eq 0 ]; then
  echo "  ✅ Already up to date with origin/main (nothing to push)"
else
  echo "  Pushing $AHEAD commit(s) to origin/main..."
  git push origin main
  echo "  ✅ Pushed"
fi

# ── summary ───────────────────────────────────────────────────────────────────
HASH=$(git rev-parse --short HEAD)
BRANCH=$(git branch --show-current 2>/dev/null || echo "main")

echo ""
echo "  Branch: $BRANCH | HEAD: $HASH | Pushed: ✅"
