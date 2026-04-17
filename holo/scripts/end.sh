#!/usr/bin/env bash
# Holo session close script. Called by /end-session.
# Usage: bash scripts/end.sh "$PWD"
set -e

PROJECT_DIR="${1:-$PWD}"
HANDOFFPACK_DIR="/Users/tealizard/Documents/handoffpack-www"

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

# ── handoffpack-www ───────────────────────────────────────────────────────────
echo ""
if [ ! -d "$HANDOFFPACK_DIR" ]; then
  echo "  ⚠️  handoffpack-www not found at $HANDOFFPACK_DIR (skipping)"
else
  WWW_AHEAD=$(git -C "$HANDOFFPACK_DIR" rev-list origin/main..HEAD --count 2>/dev/null || echo "0")
  if [ "$WWW_AHEAD" -eq 0 ]; then
    echo "  ✅ handoffpack-www already up to date"
  else
    echo "  Pushing $WWW_AHEAD commit(s) from handoffpack-www..."
    if WWW_ERR=$(git -C "$HANDOFFPACK_DIR" push origin main 2>&1); then
      echo "  ✅ handoffpack-www pushed"
    else
      echo "  ❌ handoffpack-www push failed: $WWW_ERR"
      exit 1
    fi
  fi
fi

# ── summary ───────────────────────────────────────────────────────────────────
HASH=$(git rev-parse --short HEAD)
BRANCH=$(git branch --show-current 2>/dev/null || echo "main")

echo ""
echo "  Branch: $BRANCH | HEAD: $HASH | Pushed: ✅"
