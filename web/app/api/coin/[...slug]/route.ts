// COIN API routes — Supabase-backed. Reads + writes go through @/components/lab/coin/server,
// which is RLS-scoped via the per-request authed Supabase client. Auth is enforced both
// here and in middleware.ts (defense in depth).
//
// The previous Python `careerops.web_cli` subprocess and bundled SQLite snapshot are gone.
// Mutations are first-class on prod now — no more 503 contract.

import { NextRequest, NextResponse } from 'next/server'
import {
  fetchDashboard, fetchRoles, fetchRole, fetchOffers,
  trackRoleStatus, dismissRole, appendNote, fetchDismissalReasons,
} from '@/components/lab/coin/server'
import { LANES } from '@/components/lab/coin/constants'

const PRIVATE_HEADERS = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
}

const MAX_LIMIT = 500
const DEFAULT_LIMIT = 100

function notFound(msg = 'Not found') {
  return NextResponse.json({ error: msg }, { status: 404, headers: PRIVATE_HEADERS })
}
function badRequest(msg: string) {
  return NextResponse.json({ error: msg }, { status: 400, headers: PRIVATE_HEADERS })
}
function jsonOk<T>(data: T) {
  return NextResponse.json(data, { headers: PRIVATE_HEADERS })
}

function parseLimit(raw: string | null): number | undefined {
  if (raw == null) return undefined
  const n = Number(raw)
  if (!Number.isFinite(n)) return undefined
  return Math.max(1, Math.min(MAX_LIMIT, Math.floor(n)))
}

function parseRoleId(raw: string | undefined): number | null {
  if (raw == null) return null
  const n = Number(raw)
  if (!Number.isFinite(n) || !Number.isInteger(n) || n < 0) return null
  return n
}

// ── GET ──────────────────────────────────────────────────────────────────────

export async function GET(
  _req: NextRequest,
  { params }: { params: { slug: string[] } }
) {
  const slug = params.slug ?? []
  const head = slug[0]

  try {
    if (head === 'dashboard' && slug.length === 1) {
      return jsonOk(await fetchDashboard())
    }

    if (head === 'lanes' && slug.length === 1) {
      return jsonOk(LANES)
    }

    if (head === 'roles' && slug.length === 1) {
      const sp = _req.nextUrl.searchParams
      const limit = parseLimit(sp.get('limit')) ?? DEFAULT_LIMIT
      const roles = await fetchRoles({
        status: sp.get('status') ?? undefined,
        lane:   sp.get('lane')   ?? undefined,
        limit,
      })
      return jsonOk(roles)
    }

    if (head === 'offers' && slug.length === 1) {
      return jsonOk(await fetchOffers())
    }

    if (head === 'outreach' && slug.length === 1) {
      return jsonOk([])
    }

    // GET /api/coin/dismissal-reasons — populates the "Not a Fit" picker.
    if (head === 'dismissal-reasons' && slug.length === 1) {
      return jsonOk(await fetchDismissalReasons())
    }

    if (head === 'role' && slug.length === 2) {
      const id = parseRoleId(slug[1])
      if (id == null) return badRequest('invalid role id')
      const role = await fetchRole(id)
      if (!role) return notFound(`role ${id} not found`)
      return jsonOk(role)
    }

    return notFound()
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    const detail = process.env.NODE_ENV === 'development' ? msg : 'server error'
    return NextResponse.json({ error: detail }, { status: 500, headers: PRIVATE_HEADERS })
  }
}

// ── POST ─────────────────────────────────────────────────────────────────────
// Auth is enforced by middleware.ts (Supabase session). Each handler also
// checks the user via the server-side Supabase client (defense in depth).

export async function POST(
  req: NextRequest,
  { params }: { params: { slug: string[] } }
) {
  const slug = params.slug ?? []
  const head = slug[0]

  try {
    // POST /api/coin/role/[id]/{track,dismiss,notes}
    if (head === 'role' && slug.length === 3) {
      const id = parseRoleId(slug[1])
      if (id == null) return badRequest('invalid role id')
      const action = slug[2]

      if (action === 'track') {
        const body = await req.json().catch(() => ({}))
        if (!body?.status || typeof body.status !== 'string') return badRequest('status required')
        const result = await trackRoleStatus(id, body.status, typeof body.note === 'string' ? body.note : undefined)
        if (!result.ok) {
          return NextResponse.json({ error: result.error }, { status: 400, headers: PRIVATE_HEADERS })
        }
        return jsonOk({ ok: true })
      }

      if (action === 'dismiss') {
        const body = await req.json().catch(() => ({}))
        if (!body?.reason_code || typeof body.reason_code !== 'string') {
          return badRequest('reason_code required')
        }
        const reasonText = typeof body.reason_text === 'string' ? body.reason_text : undefined
        const customText = typeof body.custom_text === 'string' ? body.custom_text : undefined
        const result = await dismissRole(id, body.reason_code, reasonText, customText)
        if (!result.ok) {
          return NextResponse.json({ error: result.error }, { status: 400, headers: PRIVATE_HEADERS })
        }
        return jsonOk({ ok: true })
      }

      if (action === 'notes') {
        const body = await req.json().catch(() => ({}))
        if (!body?.text || typeof body.text !== 'string') return badRequest('text required')
        const result = await appendNote(id, body.text)
        if (!result.ok) {
          return NextResponse.json({ error: result.error }, { status: 400, headers: PRIVATE_HEADERS })
        }
        return jsonOk({ ok: true })
      }

      // 'tailor' was a Python subprocess call. Pending the Python migration
      // it's stubbed to return a 501 with a clear message.
      if (action === 'tailor') {
        return NextResponse.json(
          { error: 'Resume tailoring is queued for the next release; run `/coin tailor <id>` in the local CLI for now.' },
          { status: 501, headers: PRIVATE_HEADERS }
        )
      }

      return notFound()
    }

    return notFound()
  } catch (err) {
    const e = err as Error
    return NextResponse.json({ error: e.message }, { status: 500, headers: PRIVATE_HEADERS })
  }
}
