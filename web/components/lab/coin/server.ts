import 'server-only'
import path from 'node:path'
import { spawn } from 'node:child_process'
import type { DashboardData, Role, Offer } from './types'

const DB_PATH = process.env.COIN_DB_PATH
  || path.resolve(process.cwd(), '../coin/data/db/pipeline.db')

const PYTHON = process.env.COIN_PYTHON
  || path.resolve(process.cwd(), '../coin/.venv/bin/python')

const COIN_CWD = path.resolve(process.cwd(), '../coin')

function openDb() {
  // Dynamic require so this only loads in Node (not in edge runtime)
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const Database = require('better-sqlite3')
  return new Database(DB_PATH, { readonly: true, fileMustExist: true })
}

export async function fetchDashboard(): Promise<DashboardData> {
  const db = openDb()
  try {
    const counts: Record<string, number> = {}
    const rows = db.prepare(
      'SELECT status, COUNT(*) as n FROM roles GROUP BY status'
    ).all() as { status: string; n: number }[]
    for (const r of rows) counts[r.status] = r.n

    const top_roles = db.prepare(`
      SELECT * FROM roles
      WHERE status NOT IN ('offer','rejected','withdrawn','no_apply','closed')
      ORDER BY fit_score DESC
      LIMIT 15
    `).all() as Role[]

    const stale_applications = db.prepare(`
      SELECT * FROM roles
      WHERE status = 'applied'
        AND updated_at < datetime('now', '-14 days')
      ORDER BY updated_at ASC
      LIMIT 10
    `).all() as Role[]

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
  try {
    let sql = 'SELECT * FROM roles WHERE 1=1'
    const params: unknown[] = []
    if (filters.status) { sql += ' AND status = ?'; params.push(filters.status) }
    if (filters.lane)   { sql += ' AND lane = ?';   params.push(filters.lane) }
    sql += ' ORDER BY fit_score DESC LIMIT ?'
    params.push(filters.limit ?? 100)
    return db.prepare(sql).all(...params) as Role[]
  } finally {
    db.close()
  }
}

export async function fetchRole(id: number): Promise<Role | null> {
  const db = openDb()
  try {
    return db.prepare('SELECT * FROM roles WHERE id = ?').get(id) as Role | null
  } finally {
    db.close()
  }
}

export async function fetchOffers(): Promise<Offer[]> {
  const db = openDb()
  try {
    const tables = db.prepare(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='offers'"
    ).get()
    if (!tables) return []
    return db.prepare(
      "SELECT * FROM offers ORDER BY received_at DESC"
    ).all() as Offer[]
  } finally {
    db.close()
  }
}

export async function runWebCli(args: string[]): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, ['-m', 'careerops.web_cli', ...args], {
      cwd: COIN_CWD,
      timeout: 15_000,
    })
    let stdout = ''
    let stderr = ''
    child.stdout.on('data', (d: Buffer) => { stdout += d.toString() })
    child.stderr.on('data', (d: Buffer) => { stderr += d.toString() })
    child.on('close', (code) => {
      try {
        const parsed = JSON.parse(stdout.trim())
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
