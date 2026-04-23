# H-1.6 — Restrict CORS to handoffpack.com origins

**Priority:** High (security)
**Effort:** LOW
**Surfaces the code-review C1 finding from 2026-04-22.**

## Problem

`api/index.py::_json_response` (line ~89) sends
`Access-Control-Allow-Origin: *` on every response. This lets any
third-party origin consume the API — including malicious browser
extensions and copy-site scrapers burning our Vercel invocation budget
and upstream (PriceCharting / eBay / pokemontcg.io) goodwill.

CLAUDE.md security rule #4 explicitly forbids `*` in production.

## Goal

Reflect only trusted origins back. Deny everything else (browser drops
the response, server still returns the payload which is fine — same
model as `vary: origin`).

## Trusted origins

- `https://www.handoffpack.com` (production)
- `https://handoffpack.com` (production, apex)
- Any `*.vercel.app` preview deploy of the `handoffpack-www` project
  (pattern match suffix)
- `http://localhost:3000` (local dev — only when `VERCEL_ENV` is unset
  or `VERCEL_ENV=development`)

## Implementation

### 1. Add helper in `api/index.py`

Near the top of the file (after imports):

```python
_PROD_ORIGINS = {
    "https://www.handoffpack.com",
    "https://handoffpack.com",
}
_PREVIEW_SUFFIX = "-handoffpack-www.vercel.app"  # verify exact pattern in Vercel dashboard

def _resolve_allowed_origin(request_origin: str) -> str | None:
    if not request_origin:
        return None
    if request_origin in _PROD_ORIGINS:
        return request_origin
    # Preview deploys: https://handoffpack-www-git-<branch>-<team>.vercel.app
    # Use a conservative suffix check. Update _PREVIEW_SUFFIX after inspecting
    # an actual preview URL.
    if request_origin.endswith(".vercel.app") and "handoffpack-www" in request_origin:
        return request_origin
    # Local dev passthrough only outside production.
    if os.environ.get("VERCEL_ENV") != "production" and request_origin.startswith("http://localhost"):
        return request_origin
    return None
```

### 2. Replace the wildcard in `_json_response`

```python
def _json_response(handler, data: dict, status: int = 200, cache: str | None = None):
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    origin = _resolve_allowed_origin(handler.headers.get("Origin", ""))
    if origin:
        handler.send_header("Access-Control-Allow-Origin", origin)
        handler.send_header("Vary", "Origin")
    handler.send_header("Cache-Control", cache or _DEFAULT_CACHE)
    handler.end_headers()
    handler.wfile.write(json.dumps(data, default=str).encode())
```

### 3. Handle OPTIONS preflight

Currently the `handler` class only implements `do_GET`. Add:

```python
def do_OPTIONS(self):
    origin = _resolve_allowed_origin(self.headers.get("Origin", ""))
    self.send_response(204 if origin else 403)
    if origin:
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "86400")
    self.end_headers()
```

### 4. Tests

Add `tests/test_cors.py`:
- Request with `Origin: https://www.handoffpack.com` → echoed back
- Request with `Origin: https://evil.com` → no CORS header (header absent)
- Request with no `Origin` header → no CORS header
- `VERCEL_ENV=production` + localhost origin → denied

## Verification

1. `curl -H "Origin: https://evil.com" -i https://holo-lac-three.vercel.app/api?action=movers`
   → should see no `Access-Control-Allow-Origin` header.
2. Same curl with `Origin: https://www.handoffpack.com` → header echoes origin.
3. Live site at handoffpack.com/lab/holo still loads movers.

## Out of scope

- Auth tokens / CSRF — H-2.0.
- Rate limiting — H-1.9.

## Commits

Single commit: `fix(holo): restrict CORS to handoffpack.com origins`
