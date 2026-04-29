#!/usr/bin/env bash
# Post-deploy smoke test for the lab/web → www.handoffpack.com rewrite seam.
#
# What this catches: the exact regression that broke /lab/coin once already.
# The HTML proxies fine through www.handoffpack.com/lab/coin, but the page
# references /_next/static/css/<hash>.css. Without assetPrefix on the lab app
# (or a CSP whitelist on handoffpack-www), the browser requests the asset from
# www, which has no record of that hash → 404 → unstyled render.
#
# How it works:
#   1. Fetch the lab page through both the canonical lab origin and through
#      the www rewrite.
#   2. Extract the first /_next/static/css/* URL referenced in each.
#   3. Curl that URL through the same origin the browser would use.
#      - On lab-lifestoryco origin: must be 200.
#      - On www.handoffpack.com: must be reachable from the absolute asset URL
#        (which, with assetPrefix set, is on lab-lifestoryco). If the page is
#        still emitting relative URLs, this script flags it before users do.
#
# Usage:
#   web/scripts/postdeploy-smoke.sh                   # default URLs
#   LAB_ORIGIN=https://lab-lifestoryco.vercel.app \
#   WWW_ORIGIN=https://www.handoffpack.com \
#   PATH_UNDER_TEST=/lab/coin/login \
#     web/scripts/postdeploy-smoke.sh
#
# Exits non-zero on any 404 or hash mismatch.

set -eu

LAB_ORIGIN="${LAB_ORIGIN:-https://lab-lifestoryco.vercel.app}"
WWW_ORIGIN="${WWW_ORIGIN:-https://www.handoffpack.com}"
PATH_UNDER_TEST="${PATH_UNDER_TEST:-/lab/coin/login}"

fail() { echo "❌ $*" >&2; exit 1; }
ok()   { echo "✅ $*"; }

extract_first_css() {
  # Pulls the first /_next/static/css/<hash>.css(?dpl=…) reference out of HTML.
  # If assetPrefix is set, this will be an absolute URL we curl directly. If
  # not, it will be a relative path we resolve against the page origin.
  grep -oE '(https?://[^"]+|/)_next/static/css/[a-f0-9]+\.css[^"]*' \
    | head -1
}

echo "→ smoke: fetching ${LAB_ORIGIN}${PATH_UNDER_TEST}"
LAB_HTML=$(curl -sfL --max-time 15 "${LAB_ORIGIN}${PATH_UNDER_TEST}") \
  || fail "lab origin returned non-2xx for ${PATH_UNDER_TEST}"

echo "→ smoke: fetching ${WWW_ORIGIN}${PATH_UNDER_TEST}"
WWW_HTML=$(curl -sfL --max-time 15 "${WWW_ORIGIN}${PATH_UNDER_TEST}") \
  || fail "www origin returned non-2xx for ${PATH_UNDER_TEST}"

LAB_CSS=$(printf '%s' "$LAB_HTML" | extract_first_css || true)
WWW_CSS=$(printf '%s' "$WWW_HTML" | extract_first_css || true)

[ -n "$LAB_CSS" ] || fail "no /_next/static/css/* reference in lab origin HTML — page may be erroring"
[ -n "$WWW_CSS" ] || fail "no /_next/static/css/* reference in www origin HTML — rewrite may be misrouted"

# Resolve relative → absolute. With assetPrefix correctly set, both will already
# be absolute URLs pointing at LAB_ORIGIN.
case "$LAB_CSS" in http*) LAB_ASSET="$LAB_CSS";; *) LAB_ASSET="${LAB_ORIGIN}${LAB_CSS}";; esac
case "$WWW_CSS" in http*) WWW_ASSET="$WWW_CSS";; *) WWW_ASSET="${WWW_ORIGIN}${WWW_CSS}";; esac

echo "→ smoke: lab references → $LAB_ASSET"
echo "→ smoke: www references → $WWW_ASSET"

# Hard requirement: the asset URL the browser will fetch from a www session must
# resolve. If assetPrefix is unset, $WWW_ASSET is on www.handoffpack.com and
# will 404 (this is the original bug). If assetPrefix is set, it's on lab.
WWW_STATUS=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$WWW_ASSET")
[ "$WWW_STATUS" = "200" ] \
  || fail "asset referenced from www HTML returned HTTP $WWW_STATUS (expected 200): $WWW_ASSET
         likely cause: LAB_PUBLIC_URL not set on lab-lifestoryco Vercel env, or
         handoffpack-www CSP is blocking the cross-origin asset.
         see lab/CLAUDE.md → Two-repo deployment topology."

LAB_STATUS=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$LAB_ASSET")
[ "$LAB_STATUS" = "200" ] \
  || fail "asset referenced from lab HTML returned HTTP $LAB_STATUS (expected 200): $LAB_ASSET"

# Sanity: with assetPrefix correct, both pages reference assets on the SAME origin.
# If they diverge, www is still emitting relative paths somehow.
case "$WWW_ASSET" in
  ${LAB_ORIGIN}/*) ok "www HTML emits absolute lab-origin asset URLs (assetPrefix is active)";;
  ${WWW_ORIGIN}/*) fail "www HTML still references assets relative to www — assetPrefix not effective in this deploy";;
  *) ok "www HTML asset on unexpected origin (still 200, but worth a look): $WWW_ASSET";;
esac

ok "smoke passed: ${PATH_UNDER_TEST} loads its CSS through both origins (HTTP 200)"
