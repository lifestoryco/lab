import 'server-only'
import fs from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'
import type { DashboardData, Role, Offer } from './types'
import { DASHBOARD_TOP_N, STALE_DAYS, TERMINAL_STATUSES } from './constants'

// Hoisted top-level require: better-sqlite3 is a native .node module and is
// in next.config.js::experimental.serverComponentsExternalPackages, which
// keeps it out of the client bundle. Top-level require gets cached by Node so
// each request reuses the same module handle (no per-call re-init cost).
// Edge runtime will never load this file because of the server-only import.
// eslint-disable-next-line @typescript-eslint/no-require-imports
const Database = require('better-sqlite3') as typeof import('better-sqlite3')
type DBHandle = InstanceType<typeof Database>

// DB resolution order:
//   1. COIN_DB_PATH env var (explicit override)
//   2. <cwd>/data/coin/pipeline.db — read-only snapshot bundled with the deploy
//   3. <cwd>/../coin/data/db/pipeline.db — local-dev source where the CLI writes
let _dbPath: string | null = null
function resolveDbPath(): string {
  if (_dbPath) return _dbPath
  if (process.env.COIN_DB_PATH) {
    _dbPath = process.env.COIN_DB_PATH
    return _dbPath
  }
  const bundled = path.resolve(process.cwd(), 'data', 'coin', 'pipeline.db')
  if (fs.existsSync(bundled)) {
    _dbPath = bundled
    return _dbPath
  }
  _dbPath = path.resolve(process.cwd(), '../coin/data/db/pipeline.db')
  return _dbPath
}

const PYTHON = process.env.COIN_PYTHON
  || path.resolve(process.cwd(), '../coin/.venv/bin/python')

const COIN_CWD = path.resolve(process.cwd(), '../coin')

// Vercel sets process.env.VERCEL=1 in deployed environments. Mutations require
// the local Python CLI + a writable DB, so they're disabled there.
export const IS_READ_ONLY = !!process.env.VERCEL

// Built once at module load — array of single-quoted SQL string literals,
// joined for an IN-clause. The set is small and finite so this is safe even
// though we're concatenating into SQL.
const TERMINAL_STATUS_SQL = Array.from(TERMINAL_STATUSES)
  .map(s => `'${s.replace(/'/g, "''")}'`)
  .join(',')

function emptyDashboard(): DashboardData {
  return {
    pipeline_counts: {},
    top_roles: [],
    stale_applications: [],
    updated_at: new Date(0).toISOString(),
  }
}

function openDb(): DBHandle | null {
  const dbPath = resolveDbPath()
  if (!fs.existsSync(dbPath)) return null
  try {
    const db = new Database(dbPath, { readonly: true })
    // Match Python's get_role() preference: stage-2 score wins over stage-1,
    // and either wins over the legacy fit_score. Compute once via a SQL view
    // alias so callers can ORDER BY this without recomputing.
    return db
  } catch (err) {
    // Path stripped from prod logs to avoid leaking deploy layout.
    if (process.env.NODE_ENV === 'development') {
      console.error('[coin/server] failed to open DB at', dbPath, err)
    } else {
      console.error('[coin/server] failed to open DB:', (err as Error).message)
    }
    return null
  }
}

/** Mirror Python's pipeline.get_role() COALESCE order: stage-2 first, then
 *  stage-1, then the legacy fit_score column. Used for ORDER BY across the
 *  read endpoints so the dashboard ranks roles the same way the CLI does. */
const AUTHORITATIVE_SCORE = 'COALESCE(score_stage2, score_stage1, fit_score)'

export async function fetchDashboard(): Promise<DashboardData> {
  const db = openDb()
  if (!db) return emptyDashboard()
  try {
    const counts: Record<string, number> = {}
    const rows = db.prepare(
      'SELECT status, COUNT(*) as n FROM roles GROUP BY status'
    ).all() as { status: string; n: number }[]
    for (const r of rows) counts[r.status] = r.n

    const top_roles = db.prepare(`
      SELECT * FROM roles
      WHERE status NOT IN (${TERMINAL_STATUS_SQL})
      ORDER BY ${AUTHORITATIVE_SCORE} DESC
      LIMIT ?
    `).all(DASHBOARD_TOP_N) as Role[]

    const stale_applications = db.prepare(`
      SELECT * FROM roles
      WHERE status = 'applied'
        AND updated_at < datetime('now', ?)
      ORDER BY updated_at ASC
      LIMIT 10
    `).all(`-${STALE_DAYS} days`) as Role[]

    return {
      pipeline_counts: counts,
      top_roles,
      stale_applications,
      updated_at: new Date().toISOString(),
    }
  } finally {
    db.close()
  }
}

export async function fetchRoles(filters: {
  status?: string; lane?: string; limit?: number
} = {}): Promise<Role[]> {
  const db = openDb()
  if (!db) return []
  try {
    let sql = 'SELECT * FROM roles WHERE 1=1'
    const params: unknown[] = []
    if (filters.status) { sql += ' AND status = ?'; params.push(filters.status) }
    if (filters.lane)   { sql += ' AND lane = ?';   params.push(filters.lane) }
    sql += ` ORDER BY ${AUTHORITATIVE_SCORE} DESC LIMIT ?`
    params.push(filters.limit ?? 100)
    return db.prepare(sql).all(...params) as Role[]
  } finally {
    db.close()
  }
}

export async function fetchRole(id: number): Promise<Role | null> {
  const db = openDb()
  if (!db) return null
  try {
    return (db.prepare('SELECT * FROM roles WHERE id = ?').get(id) as Role | undefined) ?? null
  } finally {
    db.close()
  }
}

export async function fetchOffers(): Promise<Offer[]> {
  const db = openDb()
  if (!db) return []
  try {
    const tables = db.prepare(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='offers'"
    ).get()
    if (!tables) return []
    return db.prepare(
      'SELECT * FROM offers ORDER BY received_at DESC'
    ).all() as Offer[]
  } finally {
    db.close()
  }
}

export async function runWebCli(args: string[]): Promise<unknown> {
  if (IS_READ_ONLY) {
    throw Object.assign(new Error(
      'Mutations are disabled on the deployed dashboard. Use the local Coin CLI instead.'
    ), { code: 'READ_ONLY_DEPLOYMENT', exitCode: 503 })
  }
  if (!fs.existsSync(PYTHON)) {
    throw Object.assign(new Error(
      `Python interpreter not found at ${PYTHON}. Set COIN_PYTHON or run from a checkout with coin/.venv installed.`
    ), { code: 'PYTHON_NOT_FOUND', exitCode: 503 })
  }
  return new Promise((resolve, reject) => {
    // Pass an explicit minimal env so unrelated secrets in the Next process
    // env (e.g. analytics tokens, COIN_WEB_PASSWORD) don't leak into the
    // Python subprocess.
    const minimalEnv: NodeJS.ProcessEnv = {
      PATH: process.env.PATH ?? '',
      HOME: process.env.HOME ?? '',
      NODE_ENV: process.env.NODE_ENV,
      ...(process.env.COIN_DB_PATH ? { COIN_DB_PATH: process.env.COIN_DB_PATH } : {}),
      ...(process.env.COIN_RESUMES_DIR ? { COIN_RESUMES_DIR: process.env.COIN_RESUMES_DIR } : {}),
      ...(process.env.COIN_STORIES_PATH ? { COIN_STORIES_PATH: process.env.COIN_STORIES_PATH } : {}),
    }
    const child = spawn(PYTHON, ['-m', 'careerops.web_cli', ...args], {
      cwd: COIN_CWD,
      timeout: 15_000,
      env: minimalEnv,
    })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (d: Buffer) => { stdout += d.toString() })
    child.stderr.on('data', (d: Buffer) => { stderr += d.toString() })
    child.on('close', (code) => {
      try {
        const parsed = JSON.parse(stdout.trim()) as { ok?: boolean; error?: string; code?: string }
        if (!parsed.ok) {
          reject(Object.assign(new Error(parsed.error ?? 'web_cli error'), { code: parsed.code, exitCode: code }))
        } else {
          resolve(parsed)
        }
      } catch {
        reject(new Error(`web_cli parse error (exit ${code}): ${stderr.slice(0, 200)}`))
      }
    })
  })
}
