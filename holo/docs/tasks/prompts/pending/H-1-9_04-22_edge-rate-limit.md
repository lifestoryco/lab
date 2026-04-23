# H-1.9 — Edge rate limiting (Upstash Redis + Next.js middleware)

**Priority:** High (abuse protection)
**Effort:** MED
**Surfaces the code-review H7 finding from 2026-04-22.**

## Problem

`/api/holo` is unauthenticated and does per-request scraping of
PriceCharting / eBay / pokemontcg.io. A single abusive client can:
- Burn our Vercel invocation budget
- Trigger upstream bans (PriceCharting doesn't document limits but
  scrape-aggressively and they block by IP)
- Race around the L1 `/tmp` cache by varying query params
- Exhaust the pokemontcg.io shared key quota

No auth is planned until H-2.0, so we need client-side throttling.

## Goal

Enforce a per-IP rate limit at the Next.js edge (before the Python
serverless function even wakes up). Limit tunable per action —
cheap cached endpoints (movers, meta) get a higher ceiling than
expensive ones (flip, history).

## Design

### 1. Storage: Upstash Redis (serverless-native)

Free tier gives 10k commands/day — enough for ~5k active users at
our allowance. Add integration in Vercel dashboard:
- `UPSTASH_REDIS_REST_URL`
- `UPSTASH_REDIS_REST_TOKEN`

### 2. Middleware: `handoffpack-www/middleware.ts`

```ts
import { NextRequest, NextResponse } from 'next/server'
import { Ratelimit } from '@upstash/ratelimit'
import { Redis } from '@upstash/redis'

export const config = {
  matcher: ['/api/holo/:path*'],
}

const redis = Redis.fromEnv()

// Per-action budgets. Sliding-window.
const LIMITS: Record<string, Ratelimit> = {
  movers:  new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(120, '1 m') }),
  meta:    new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(120, '1 m') }),
  search:  new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(60,  '1 m') }),
  history: new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(30,  '1 m') }),
  flip:    new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(30,  '1 m') }),
  gradeit: new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(20,  '1 m') }),
  pokedex: new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(60,  '1 m') }),
  _default: new Ratelimit({ redis, limiter: Ratelimit.slidingWindow(60,  '1 m') }),
}

export async function middleware(req: NextRequest) {
  const ip = req.ip ?? req.headers.get('x-forwarded-for')?.split(',')[0] ?? 'anon'
  const action = req.nextUrl.searchParams.get('action') ?? '_default'
  const limiter = LIMITS[action] ?? LIMITS._default
  const { success, limit, remaining, reset } = await limiter.limit(`${ip}:${action}`)

  const headers = new Headers({
    'X-RateLimit-Limit':     String(limit),
    'X-RateLimit-Remaining': String(remaining),
    'X-RateLimit-Reset':     String(reset),
  })

  if (!success) {
    return new NextResponse(
      JSON.stringify({ error: 'rate_limited', retry_after_ms: reset - Date.now() }),
      { status: 429, headers: { ...Object.fromEntries(headers), 'Content-Type': 'application/json' } },
    )
  }

  const res = NextResponse.next()
  headers.forEach((v, k) => res.headers.set(k, v))
  return res
}
```

### 3. Package deps

```bash
cd handoffpack-www
npm install @upstash/ratelimit @upstash/redis
```

### 4. Frontend: handle 429

In `HoloPage.tsx`, wrap each fetch site to detect 429 and show a
user-facing "You're being rate-limited, wait a moment" toast
instead of a generic error. The `retry_after_ms` field tells us
how long to wait before re-enabling the button.

### 5. IP-identification edge cases

- Vercel's `req.ip` is populated. Fall back to
  `x-forwarded-for[0]` if not.
- Shared NATs (corporate office, carrier CGNAT) will all share one
  bucket. Acceptable for v1 — if we see false-positive complaints,
  add a per-session cookie bucket as a secondary key.

### 6. Tests

- Manual: curl the endpoint 200 times in a loop, expect 429 after
  the window fills.
- Jest test for middleware:
  ```ts
  test('429 after limit exceeded', async () => { ... })
  ```

### 7. Monitoring

Emit a PostHog event on every 429 with `{action, ip_hash}` so we
can see abusers' patterns without storing raw IPs.

## Rollout plan

1. Deploy middleware with generous limits (2x intended ceiling).
2. Watch 429 rate in PostHog for 24h.
3. Dial limits down to target once confident no legit users trip.

## Out of scope

- Auth-scoped rate limits (H-2.0 will add user tiers).
- Global per-action budget (e.g. stop all flip calls when
  pokemontcg.io quota is near limit) — future task.

## Commits

1. `feat(lab/holo): edge rate limiting via Upstash Redis`
2. `feat(lab/holo): user-facing 429 handling with retry-after toast`
