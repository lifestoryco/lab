# H-1.7 — Share HTTP keep-alive session between api/ and pokequant/

**Priority:** Medium (perf)
**Effort:** MED
**Surfaces the code-review H2 finding from 2026-04-22.**

## Problem

`api/index.py::_http_session()` creates a module-level `requests.Session`
with a connection pool (16/32) and reuses it across warm invocations.
But the scraper in `pokequant/scraper.py` calls `requests.get(...)`
directly at:
- `scraper.py:837` — TCGPlayer redirect resolver
- `scraper.py:892` — TCGPlayer infinite-api history
- `scraper.py:979` (via `_get`) — eBay
- PriceCharting (via `_get`)
- `pokemontcg.io` (via `_get`)

Each of those opens a fresh TCP + TLS handshake (~150ms on typical
Vercel cold warmup). On a movers fan-out (8 parallel threads × ~2
sources each) that's 16 handshakes — plus whatever retries happen.

## Goal

Single shared `requests.Session` with connection pooling, used by both
the api entrypoint and every outbound call in `pokequant/`. Save
~100–300ms per outbound call on warm instances.

## Design

### 1. New module: `pokequant/http.py`

Thread-safe singleton. No imports from `api/` (directional rule).

```python
"""Shared requests.Session with connection pooling.

Used for every outbound HTTP call in holo — from both the Vercel
entrypoint and the scraper helpers. Reusing a single Session lets the
TCP+TLS handshake amortize across warm-instance invocations.
"""
from __future__ import annotations

import threading
from typing import Optional

import requests
from requests.adapters import HTTPAdapter

_SESSION: Optional[requests.Session] = None
_LOCK = threading.Lock()


def session() -> requests.Session:
    global _SESSION
    if _SESSION is not None:
        return _SESSION
    with _LOCK:
        if _SESSION is None:
            s = requests.Session()
            adapter = HTTPAdapter(
                pool_connections=16,
                pool_maxsize=32,
                max_retries=0,
            )
            s.mount("https://", adapter)
            s.mount("http://", adapter)
            _SESSION = s
    return _SESSION
```

### 2. Replace `api/index.py::_http_session`

Delete the local implementation; re-export for backwards compat inside
the file, or update all `_http_session()` call sites to
`from pokequant.http import session as _http_session`.

### 3. Migrate scraper call sites

Every `requests.get(...)` → `session().get(...)`:

- `_get()` helper (used for PC + eBay + pokemontcg.io) — swap the
  internal `requests.get` for `session().get`. Keep per-call timeout
  + headers args.
- `_lookup_tcgplayer_product_id` redirect call (line ~837) — use
  `session().get` with `allow_redirects=False`.
- `_fetch_tcgplayer_history` — use `session().get`.

**Careful:** the `_get()` helper currently does retry/backoff logic
and UA rotation. Keep that wrapping intact; only replace the bare
`requests.get` call inside it.

### 4. Tests

Update `tests/test_scraper.py` mocks. Any test that patched
`requests.get` now needs to patch `pokequant.http.session` or use
a `requests_mock` session adapter. Easiest migration:

```python
@patch("pokequant.http.session")
def test_fetch_sales_...(mock_session):
    mock_session.return_value.get.return_value = ...
```

### 5. Verification

- `.venv/bin/pytest tests/ -q` → 57/57 still passing.
- Deploy to preview, load `/lab/holo`, compare movers p50 latency
  before/after. Expect ~10-20% improvement on warm instances.
- `curl -w "%{time_total}\n" -o /dev/null -s <api>?action=movers`
  twice in a row — second call should be noticeably faster.

## Risks

- SQLite `_product_id_cache_put` runs inside the redirect call site —
  switching to a shared session doesn't affect sqlite, but watch
  logs after deploy.
- Session threading: `requests.Session` is thread-safe for independent
  requests but not for shared state mutation. Don't mutate headers on
  the shared session mid-request — use per-call `headers=` arg.

## Commits

Single commit: `perf(holo): share HTTP keep-alive session across api and scraper`
