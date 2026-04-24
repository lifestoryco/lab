#!/bin/bash
# Coin session end — validate clean state and push

PROJECT_DIR="${1:-$PWD}"
cd "$PROJECT_DIR" || exit 1

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --staged --quiet; then
  echo "⚠️  Uncommitted changes — commit everything before ending session"
  git status --short
  exit 1
fi

# Push
echo "Pushing to origin..."
if git push origin "$(git branch --show-current)"; then
  echo "✅ Pushed — HEAD: $(git rev-parse --short HEAD)"
else
  echo "❌ Push failed"
  exit 1
fi
