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
# IMPORTANT: push HEAD:main, not "main". This script commonly runs from a
# worktree branch (e.g. claude/laughing-nobel-*). `git push origin main`
# pushes the LOCAL `main` ref — which on a worktree branch is stale. Git
# then says "Everything up-to-date" and the commits never leave the feature
# branch. Pushing HEAD:main advances origin/main to the current HEAD, but
# only when it's a clean fast-forward; otherwise we fail loud.
git fetch origin main --quiet 2>/dev/null || true
AHEAD=$(git rev-list origin/main..HEAD --count 2>/dev/null || echo "0")
BEHIND=$(git rev-list HEAD..origin/main --count 2>/dev/null || echo "0")

if [ "$AHEAD" -eq 0 ] && [ "$BEHIND" -eq 0 ]; then
  echo "  ✅ Already up to date with origin/main (nothing to push)"
elif [ "$BEHIND" -gt 0 ]; then
  echo "  ❌ HEAD has diverged from origin/main ($BEHIND behind, $AHEAD ahead)."
  echo "     Refusing to push — you'd lose remote commits. Resolve first:"
  echo "       git fetch origin && git rebase origin/main"
  exit 1
else
  CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "HEAD")
  echo "  Fast-forwarding origin/main by $AHEAD commit(s) (from $CURRENT_BRANCH)..."
  if ! git push origin HEAD:main; then
    echo "  ❌ Push to origin/main failed."
    exit 1
  fi
  # Keep local `main` in sync so other worktrees pick up the advance on
  # their next fetch. Skip if main is checked out in THIS worktree
  # (update-ref would refuse; push already moved the tip).
  if [ "$CURRENT_BRANCH" != "main" ] && git show-ref --verify --quiet refs/heads/main; then
    git update-ref refs/heads/main HEAD 2>/dev/null || true
  fi
  echo "  ✅ Pushed (origin/main now at $(git rev-parse --short HEAD))"
fi

# ── handoffpack-www ───────────────────────────────────────────────────────────
echo ""
if [ ! -d "$HANDOFFPACK_DIR" ]; then
  echo "  ⚠️  handoffpack-www not found at $HANDOFFPACK_DIR (skipping)"
else
  git -C "$HANDOFFPACK_DIR" fetch origin main --quiet 2>/dev/null || true
  WWW_AHEAD=$(git -C "$HANDOFFPACK_DIR" rev-list origin/main..HEAD --count 2>/dev/null || echo "0")
  WWW_BEHIND=$(git -C "$HANDOFFPACK_DIR" rev-list HEAD..origin/main --count 2>/dev/null || echo "0")
  if [ "$WWW_AHEAD" -eq 0 ] && [ "$WWW_BEHIND" -eq 0 ]; then
    echo "  ✅ handoffpack-www already up to date"
  elif [ "$WWW_BEHIND" -gt 0 ]; then
    echo "  ❌ handoffpack-www HEAD diverged from origin/main ($WWW_BEHIND behind, $WWW_AHEAD ahead)."
    echo "     Resolve manually: cd $HANDOFFPACK_DIR && git fetch && git rebase origin/main"
    exit 1
  else
    echo "  Pushing $WWW_AHEAD commit(s) from handoffpack-www..."
    # Push HEAD:main (same reasoning as the holo push above — handoffpack-www
    # may also be on a feature branch in the future).
    if WWW_ERR=$(git -C "$HANDOFFPACK_DIR" push origin HEAD:main 2>&1); then
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
