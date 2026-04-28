#!/usr/bin/env bash
# Refuse to build if .vercel/project.json is bound to the wrong Vercel project.
#
# Enforces the lifestoryco/lab ↔ Vercel boundary documented in
# /Users/tealizard/Documents/lab/CLAUDE.md. The lab repo's web/ tree must NEVER
# be deployed to the `handoffpack-www` project — that's the marketing site.
# It must be deployed to `lab-lifestoryco`.
#
# Vercel itself does NOT ship .vercel/project.json into the build env, so on
# Vercel this script no-ops. The guard is for local `vercel --prod` invocations
# from a developer machine, which IS where the wrong-link clobber happened.

set -eu

PROJECT_FILE=".vercel/project.json"

# Vercel's build env does not include the .vercel/ directory — no file = no check.
if [ ! -f "$PROJECT_FILE" ]; then
  echo "predeploy-check: no $PROJECT_FILE present (likely a CI/Vercel build); skipping link check."
  exit 0
fi

# Extract projectName via grep+sed; jq is not guaranteed to be installed.
PROJECT_NAME=$(grep -o '"projectName"[[:space:]]*:[[:space:]]*"[^"]*"' "$PROJECT_FILE" \
  | head -1 \
  | sed -E 's/.*"([^"]*)"$/\1/' || true)

if [ -z "${PROJECT_NAME:-}" ]; then
  # Vercel's own builder writes a stripped-down project.json without
  # projectName. Without a name we can't enforce; treat as a no-op.
  echo "predeploy-check: $PROJECT_FILE present but no projectName field; skipping (likely Vercel builder)."
  exit 0
fi

case "$PROJECT_NAME" in
  lab-lifestoryco|lab)
    echo "predeploy-check: linked to '$PROJECT_NAME' — ok."
    exit 0
    ;;
  *)
    cat >&2 <<EOF
predeploy-check: refusing to build for Vercel project "$PROJECT_NAME".

This is the lifestoryco/lab repo. It must only deploy to:
  lab-lifestoryco  (or "lab" as a future-proof alias)

Most likely cause: 'vercel link' picked the wrong project. Fix:
  rm -rf .vercel
  vercel link --project lab-lifestoryco --yes

If you're intentionally adding a new project name, edit the case
in $0 to whitelist it.

See /Users/tealizard/Documents/lab/CLAUDE.md for the two-repo
deployment topology.
EOF
    exit 1
    ;;
esac
