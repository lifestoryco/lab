// Architecture reference: /lab/holo uses a similar proxy pattern for Python backend work.
// Read path: better-sqlite3 via server.ts (zero-latency, no subprocess).
// Mutation path: subprocess to careerops.web_cli (keeps Python as source of truth for
//   state-machine validation, comp math, tailoring logic — no drift between Node and Python).
//
// On Vercel (`process.env.VERCEL`), POST endpoints return 503 — see README.md.

import { NextRequest, NextResponse } from 'next/server'
import path from 'node:path'
import fs from 'node:fs'
import { Readable } from 'node:stream'
import {
  fetchDashboard, fetchRoles, fetchRole, fetchOffers, runWebCli,
} from '@/components/lab/coin/server'
import { LANES } from '@/components/lab/coin/constants'

const RESUMES_DIR = process.env.COIN_RESUMES_DIR
  || path.resolve(process.cwd(), '../coin/data/resumes/generated')

const STORIES_PATH = process.env.COIN_STORIES_PATH
  || path.resolve(process.cwd(), '../coin/data/resumes/stories.yml')

const PRIVATE_HEADERS = {
  'Cache-Control': 'private, no-store',
  'X-Content-Type-Options': 'nosniff',
}

// Hard cap on `?limit=` so a stray ?limit=99999999 can't pin the DB.
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
  req: NextRequest,
  { params }: { params: { slug: string[] } }
) {
  const slug = params.slug ?? []
  const head = slug[0]

  try {
    // GET /api/coin/dashboard
    if (head === 'dashboard' && slug.length === 1) {
      return jsonOk(await fetchDashboard())
    }

    // GET /api/coin/lanes — surface canonical archetype list to the client.
    if (head === 'lanes' && slug.length === 1) {
      return jsonOk(LANES)
    }

    // GET /api/coin/roles?status=&lane=&limit=
    if (head === 'roles' && slug.length === 1) {
      const sp = req.nextUrl.searchParams
      const limit = parseLimit(sp.get('limit')) ?? DEFAULT_LIMIT
      const roles = await fetchRoles({
        status: sp.get('status') ?? undefined,
        lane:   sp.get('lane')   ?? undefined,
        limit,
      })
      return jsonOk(roles)
    }

    // GET /api/coin/offers
    if (head === 'offers' && slug.length === 1) {
      return jsonOk(await fetchOffers())
    }

    // GET /api/coin/outreach — table is optional; degrade to [] if absent.
    if (head === 'outreach' && slug.length === 1) {
      return jsonOk([])
    }

    // GET /api/coin/stories — raw YAML text. Empty 200 if missing (clients
    // already handle empty as "no stories captured yet").
    if (head === 'stories' && slug.length === 1) {
      if (!fs.existsSync(STORIES_PATH)) {
        return new NextResponse('', { headers: { 'Content-Type': 'application/yaml; charset=utf-8', ...PRIVATE_HEADERS } })
      }
      const text = fs.readFileSync(STORIES_PATH, 'utf-8')
      return new NextResponse(text, {
        headers: { 'Content-Type': 'application/yaml; charset=utf-8', ...PRIVATE_HEADERS },
      })
    }

    // GET /api/coin/role/[id]
    if (head === 'role' && slug.length === 2) {
      const id = parseRoleId(slug[1])
      if (id == null) return badRequest('invalid role id')
      const role = await fetchRole(id)
      if (!role) return notFound(`role ${id} not found`)
      return jsonOk(role)
    }

    // GET /api/coin/role/[id]/pdf
    if (head === 'role' && slug.length === 3 && slug[2] === 'pdf') {
      const id = parseRoleId(slug[1])
      if (id == null) return badRequest('invalid role id')
      const prefix = String(id).padStart(4, '0')
      let pdfPath: string | null = null
      if (fs.existsSync(RESUMES_DIR)) {
        const files = fs.readdirSync(RESUMES_DIR)
          .filter(f => f.startsWith(prefix) && f.endsWith('.pdf'))
          .sort()
          .reverse()
        if (files.length) pdfPath = path.join(RESUMES_DIR, files[0])
      }
      if (!pdfPath) return notFound('no PDF generated for this role')
      // Adapt Node Readable → web ReadableStream (Node 18+).
      const webStream = Readable.toWeb(fs.createReadStream(pdfPath)) as unknown as ReadableStream
      return new NextResponse(webStream, {
        headers: { 'Content-Type': 'application/pdf', ...PRIVATE_HEADERS },
      })
    }

    return notFound()
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    const detail = process.env.NODE_ENV === 'development' ? msg : 'server error'
    return NextResponse.json({ error: detail }, { status: 500, headers: PRIVATE_HEADERS })
  }
}

// ── POST ─────────────────────────────────────────────────────────────────────

export async function POST(
  req: NextRequest,
  { params }: { params: { slug: string[] } }
) {
  const slug = params.slug ?? []
  const head = slug[0]

  // POST /api/coin/login
  if (head === 'login' && slug.length === 1) {
    const pwd = process.env.COIN_WEB_PASSWORD
    if (!pwd) {
      // No password configured → no gate. Hand back a benign ok with no cookie.
      return jsonOk({ ok: true })
    }
    const body = await req.json().catch(() => ({}))
    if (typeof body?.password !== 'string' || body.password !== pwd) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401, headers: PRIVATE_HEADERS })
    }
    const res = NextResponse.json({ ok: true }, { headers: PRIVATE_HEADERS })
    res.cookies.set('coin_auth', pwd, {
      httpOnly: true,
      sameSite: 'lax',
      secure: process.env.NODE_ENV === 'production',
      path: '/',
      maxAge: 60 * 60 * 24 * 14, // 14 days
    })
    return res
  }

  // Auth gate for all other POST endpoints. Middleware also enforces this;
  // duplication is intentional (defense in depth in case middleware is bypassed).
  const pwd = process.env.COIN_WEB_PASSWORD
  if (pwd) {
    const cookie = req.cookies.get('coin_auth')?.value
    if (cookie !== pwd) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401, headers: PRIVATE_HEADERS })
    }
  }

  try {
    // POST /api/coin/role/[id]/{track,tailor,notes}
    if (head === 'role' && slug.length === 3) {
      const id = parseRoleId(slug[1])
      if (id == null) return badRequest('invalid role id')
      const action = slug[2]

      if (action === 'track') {
        const body = await req.json().catch(() => ({}))
        if (!body?.status || typeof body.status !== 'string') return badRequest('status required')
        const args = ['track', '--id', String(id), '--status', body.status]
        if (body.note && typeof body.note === 'string') args.push('--note', body.note)
        return jsonOk(await runWebCli(args))
      }

      if (action === 'tailor') {
        return jsonOk(await runWebCli(['tailor', '--id', String(id)]))
      }

      if (action === 'notes') {
        const body = await req.json().catch(() => ({}))
        if (!body?.text || typeof body.text !== 'string') return badRequest('text required')
        return jsonOk(await runWebCli(['notes', '--id', String(id), '--append', body.text]))
      }

      return notFound()
    }

    return notFound()
  } catch (err) {
    const e = err as Error & { code?: string; exitCode?: number }
    let status = 500
    if (e.code === 'READ_ONLY_DEPLOYMENT' || e.code === 'PYTHON_NOT_FOUND') status = 503
    else if (e.exitCode === 1) status = 400
    return NextResponse.json({ error: e.message, code: e.code }, { status, headers: PRIVATE_HEADERS })
  }
}
