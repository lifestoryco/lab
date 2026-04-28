'use client'
import { useEffect, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import type { Role } from './types'
import { GRADE_COLORS, LANE_COLORS, gradeForScore, safeUrl } from './constants'

function companyInitials(name: string): string {
  return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

function hashColor(s: string): string {
  let h = 0
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) & 0xffffff
  const hue = (h % 360 + 360) % 360
  return `hsl(${hue}, 55%, 35%)`
}

function ageLabel(posted_at: string | null, now: number): string | null {
  if (!posted_at) return null
  const days = Math.floor((now - new Date(posted_at).getTime()) / 86400000)
  if (days < 7)  return `${days}d`
  if (days < 30) return `${Math.floor(days / 7)}w`
  return 'stale'
}

export function RoleCard({ role, onClick }: { role: Role; onClick: () => void }) {
  // Date.now() at render time would cause SSR hydration drift on cards near
  // a day boundary (server vs client picks different `days` value). Compute
  // age client-only after mount.
  const [now, setNow] = useState<number | null>(null)
  useEffect(() => { setNow(Date.now()) }, [])

  const laneColor = LANE_COLORS[role.lane] ?? '#888'
  const grade = role.fit_grade ?? gradeForScore(role.fit_score)
  const gradeColor = GRADE_COLORS[grade] ?? '#888'
  const age = now != null ? ageLabel(role.posted_at, now) : null
  const stale = age === 'stale'
  // Stage badge only shows when stage 2 (deep-scored) — S1 is the default and
  // adding a badge to every card is just visual noise.
  const isDeepScored = role.score_stage2 != null
  const url = safeUrl(role.url)

  const handleKey = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      onClick()
    }
  }

  return (
    <button
      type="button"
      onClick={onClick}
      onKeyDown={handleKey}
      aria-label={`Open details for ${role.title} at ${role.company}`}
      className="w-full text-left bg-zinc-900 border border-zinc-800 rounded-lg p-3 cursor-pointer hover:border-zinc-600 focus-visible:border-violet-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/50 transition-colors select-none"
    >
      <div className="flex items-start gap-2">
        {/* Company logo placeholder */}
        <div
          aria-hidden="true"
          className="w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold shrink-0"
          style={{ backgroundColor: hashColor(role.company ?? '') }}
        >
          {companyInitials(role.company ?? '?')}
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-sm text-white font-medium truncate">{role.title}</div>
          <div className="flex items-center gap-1 text-xs text-zinc-400 truncate">
            <span className="truncate">{role.company}</span>
            {url && (
              <a
                href={url}
                target="_blank"
                rel="noreferrer"
                onClick={e => e.stopPropagation()}
                aria-label={`Open ${role.company} job posting in a new tab`}
                title="Open job posting"
                className="text-zinc-500 hover:text-violet-400 transition-colors shrink-0"
              >
                <ExternalLink size={11} aria-hidden="true" />
              </a>
            )}
          </div>
        </div>

        {/* Grade circle */}
        <div
          aria-label={`Fit grade ${grade}`}
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
          style={{ backgroundColor: gradeColor + '22', border: `1.5px solid ${gradeColor}`, color: gradeColor }}
        >
          {grade}
        </div>
      </div>

      <div className="flex items-center gap-1.5 mt-2 flex-wrap">
        {/* Lane badge */}
        <span
          title={role.lane}
          className="text-xs px-1.5 py-0.5 rounded font-medium"
          style={{ backgroundColor: laneColor + '22', color: laneColor }}
        >
          {role.lane?.split('-').slice(0, 2).join('-')}
        </span>

        {/* Age badge */}
        {age && (
          <span className={`text-xs px-1.5 py-0.5 rounded ${stale ? 'bg-red-900/40 text-red-400' : 'bg-zinc-800 text-zinc-400'}`}>
            {age}
          </span>
        )}

        {/* Comp */}
        {role.comp_min != null && (
          <span
            aria-label="Compensation range"
            className="text-xs px-1.5 py-0.5 rounded bg-emerald-900/30 text-emerald-400 font-mono tabular-nums"
          >
            ${Math.round(role.comp_min / 1000)}K{role.comp_max ? `–$${Math.round(role.comp_max / 1000)}K` : '+'}
          </span>
        )}

        {/* Stage badge — only when deep-scored (stage 2). S1 is the default,
            no value in plastering [S1] on every card. */}
        {isDeepScored && (
          <span className="text-xs px-1 py-0.5 rounded font-mono ml-auto text-cyan-400 bg-cyan-950/40" title="Deep-scored (stage 2 — JD-aware)">
            S2
          </span>
        )}
      </div>
    </button>
  )
}
