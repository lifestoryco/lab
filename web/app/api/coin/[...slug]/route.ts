// Architecture reference: /lab/holo uses a similar proxy pattern for Python backend work.
// Read path: better-sqlite3 via server.ts (zero-latency, no subprocess).
// Mutation path: subprocess to careerops.web_cli (keeps Python as source of truth for
//   state-machine validation, comp math, tailoring logic — no drift between Node and Python).

import { NextRequest, NextResponse } from 'next/server'
import path from 'node:path'
import fs from 'node:fs'
import { fetchDashboard, fetchRoles, fetchRole, fetchOffers, runWebCli } from '@/components/lab/coin/server'

const RESUMES_DIR = process.env.COIN_RESUMES_DIR
  || path.resolve(process.cwd(), '../coin/data/resumes/generated')

const STORIES_PATH = process.env.COIN_STORIES_PATH
  || path.resolve(process.cwd(), '../coin/data/resumes/stories.yml')

function notFound(msg = 'Not found') {
  return NextResponse.json({ error: msg }, { status: 404 })
}

function badRequest(msg: string) {
  return NextResponse.json({ error: msg }, { status: 400 })
}

// ── GET ──────────────────────────────────────────────────────────────────────

export async function GET(
  req: NextRequest,
  { params }: { params: { slug: string[] } }
) {
  const slug = params.slug

  try {
    // GET /api/coin/dashboard
    if (slug[0] === 'dashboard') {
      const data = await fetchDashboard()
      return NextResponse.json(data)
    }

    // GET /api/coin/roles?status=&lane=&limit=
    if (slug[0] === 'roles' && slug.length === 1) {
      const sp = req.nextUrl.searchParams
      const roles = await fetchRoles({
        status: sp.get('status') ?? undefined,
        lane:   sp.get('lane')   ?? undefined,
        limit:  sp.get('limit') ? Number(sp.get('limit')) : undefined,
      })
      return NextResponse.json(roles)
    }

    // GET /api/coin/role/[id]
    if (slug[0] === 'role' && slug.length === 2) {
      const id = Number(slug[1])
      if (isNaN(id)) return badRequest('invalid role id')
      const role = await fetchRole(id)
      if (!role) return notFound(`role ${id} not found`)
      return NextResponse.json(role)
    }

    // GET /api/coin/role/[id]/pdf
    if (slug[0] === 'role' && slug[2] === 'pdf') {
      const id = Number(slug[1])
      if (isNaN(id)) return badRequest('invalid role id')
      // Find latest PDF for this role (pattern: NNNN_lane_*.pdf)
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
      const stream = fs.createReadStream(pdfPath)
      // @ts-expect-error ReadableStream vs NodeJS.ReadableStream
      return new NextResponse(stream, {
        headers: { 'Content-Type': 'application/pdf' },
      })
    }

    // GET /api/coin/offers
    if (slug[0] === 'offers' && slug.length === 1) {
      const offers = await fetchOffers()
      return NextResponse.json(offers)
    }

    // GET /api/coin/stories
    if (slug[0] === 'stories') {
      if (!fs.existsSync(STORIES_PATH)) return NextResponse.json([])
      // Return raw YAML text; client parses or displays as-is
      const text = fs.readFileSync(STORIES_PATH, 'utf-8')
      return new NextResponse(text, { headers: { 'Content-Type': 'text/plain' } })
    }

    return notFound()
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    // Only include detail in dev — don't leak paths to production
    const detail = process.env.NODE_ENV === 'development' ? msg : 'server error'
    return NextResponse.json({ error: detail }, { status: 500 })
  }
}

// ── POST ─────────────────────────────────────────────────────────────────────

export async function POST(
  req: NextRequest,
  { params }: { params: { slug: string[] } }
) {
  const slug = params.slug

  // POST /api/coin/login
  if (slug[0] === 'login') {
    const pwd = process.env.COIN_WEB_PASSWORD
    if (!pwd) return NextResponse.json({ ok: true }) // no auth in dev
    const body = await req.json().catch(() => ({}))
    if (body.password !== pwd) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const res = NextResponse.json({ ok: true })
    res.cookies.set('coin_auth', pwd, { httpOnly: true, sameSite: 'lax', path: '/' })
    return res
  }

  // Auth gate for all other POST endpoints
  const pwd = process.env.COIN_WEB_PASSWORD
  if (pwd) {
    const cookie = req.cookies.get('coin_auth')?.value
    if (cookie !== pwd) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
  }

  try {
    // POST /api/coin/role/[id]/track  { status, note? }
    if (slug[0] === 'role' && slug[2] === 'track') {
      const id = Number(slug[1])
      if (isNaN(id)) return badRequest('invalid role id')
      const body = await req.json()
      if (!body.status) return badRequest('status required')
      const args = ['track', '--id', String(id), '--status', body.status]
      if (body.note) args.push('--note', body.note)
      const result = await runWebCli(args)
      return NextResponse.json(result)
    }

    // POST /api/coin/role/[id]/tailor
    if (slug[0] === 'role' && slug[2] === 'tailor') {
      const id = Number(slug[1])
      if (isNaN(id)) return badRequest('invalid role id')
      const result = await runWebCli(['tailor', '--id', String(id)])
      return NextResponse.json(result)
    }

    // POST /api/coin/role/[id]/notes  { text }
    if (slug[0] === 'role' && slug[2] === 'notes') {
      const id = Number(slug[1])
      if (isNaN(id)) return badRequest('invalid role id')
      const body = await req.json()
      if (!body.text) return badRequest('text required')
      const result = await runWebCli(['notes', '--id', String(id), '--append', body.text])
      return NextResponse.json(result)
    }

    return notFound()
  } catch (err) {
    const e = err as Error & { code?: string; exitCode?: number }
    const status = e.exitCode === 1 ? 400 : 500
    return NextResponse.json({ error: e.message, code: e.code }, { status })
  }
}
