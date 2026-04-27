#!/bin/bash
# Coin session end — validate clean state, push branch, and merge to main.
#
# Behavior:
#   - On main: just push.
#   - On a `claude/*` branch (the standard worktree pattern): push the branch,
#     then merge --no-ff into main from the main worktree, then push main.
#   - On any other branch: push the branch and ask the user to merge manually.
#
# Why: the previous version only pushed the current branch, so worktree work
# never landed on main and new sessions couldn't see it.

set -e

PROJECT_DIR="${1:-$PWD}"
cd "$PROJECT_DIR" || exit 1

# ─── Step 1: clean working tree ──────────────────────────────────────────────
if ! git diff --quiet || ! git diff --staged --quiet; then
  echo "⚠️  Uncommitted changes — commit everything before ending session"
  git status --short
  exit 1
fi

BRANCH="$(git branch --show-current)"
SHORT_HEAD="$(git rev-parse --short HEAD)"

# ─── Step 2: push current branch ─────────────────────────────────────────────
echo "Pushing $BRANCH to origin..."
if ! git push origin "$BRANCH"; then
  echo "❌ Push of $BRANCH failed"
  exit 1
fi
echo "✅ Pushed $BRANCH — HEAD: $SHORT_HEAD"

# If we're already on main, we're done.
if [ "$BRANCH" = "main" ]; then
  exit 0
fi

# ─── Step 3: merge into main (claude/* branches only) ────────────────────────
case "$BRANCH" in
  claude/*) ;;
  *)
    echo ""
    echo "ℹ️  $BRANCH pushed but NOT merged to main."
    echo "    Non-claude branches require manual merge — this script only"
    echo "    auto-merges the standard claude/<name> worktree pattern."
    exit 0
    ;;
esac

MAIN_WT="$(git worktree list --porcelain | awk '
  /^worktree / { wt = $2 }
  /^branch refs\/heads\/main$/ { print wt; exit }
')"

if [ -z "$MAIN_WT" ]; then
  echo ""
  echo "⚠️  No worktree with [main] checked out — cannot auto-merge."
  echo "    Branch is pushed; merge it manually:"
  echo "      git checkout main && git pull && git merge --no-ff $BRANCH && git push origin main"
  exit 0
fi

if [ "$MAIN_WT" = "$PROJECT_DIR" ]; then
  echo ""
  echo "⚠️  Already in the main worktree but branch != main — refusing to self-merge."
  echo "    Investigate: $(git branch --show-current) vs main"
  exit 1
fi

echo ""
echo "Merging $BRANCH into main from $MAIN_WT ..."

# Use a subshell so `cd` doesn't leak to the calling session.
(
  cd "$MAIN_WT" || exit 1

  if ! git diff --quiet || ! git diff --staged --quiet; then
    echo "❌ Main worktree at $MAIN_WT has uncommitted changes — refusing to merge."
    git -C "$MAIN_WT" status --short
    exit 1
  fi

  git pull --ff-only origin main || {
    echo "❌ git pull --ff-only origin main failed in main worktree"
    exit 1
  }

  # Generate a sensible merge subject from the branch name.
  MERGE_MSG="merge: $BRANCH ($SHORT_HEAD)"

  if ! git merge --no-ff "$BRANCH" -m "$MERGE_MSG"; then
    echo "❌ Merge failed (likely a conflict). Resolve in $MAIN_WT and push manually."
    exit 1
  fi

  if ! git push origin main; then
    echo "❌ Push of main failed"
    exit 1
  fi
) || exit 1

NEW_MAIN_HEAD="$(git -C "$MAIN_WT" rev-parse --short main)"
echo "✅ Merged $BRANCH → main and pushed (main HEAD: $NEW_MAIN_HEAD)"
