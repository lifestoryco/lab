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
