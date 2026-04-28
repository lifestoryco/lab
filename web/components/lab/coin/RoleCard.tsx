'use client'
import type { Role } from './types'

const LANE_COLORS: Record<string, string> = {
  'mid-market-tpm': '#3b82f6',
  'enterprise-sales-engineer': '#22c55e',
  'iot-solutions-architect': '#a855f7',
  'revenue-ops-operator': '#f59e0b',
}

const GRADE_COLORS: Record<string, string> = {
  A: '#22c55e', B: '#86efac', C: '#facc15', D: '#f97316', F: '#ef4444',
}

function companyInitials(name: string): string {
  return name.split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
}

function hashColor(s: string): string {
  let h = 0
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) & 0xffffff
  const hue = (h % 360 + 360) % 360
  return `hsl(${hue}, 55%, 35%)`
}

function ageLabel(posted_at: string | null): string | null {
  if (!posted_at) return null
  const days = Math.floor((Date.now() - new Date(posted_at).getTime()) / 86400000)
  if (days < 7)  return `${days}d`
  if (days < 30) return `${Math.floor(days / 7)}w`
  return 'stale'
}

export function RoleCard({ role, onClick }: { role: Role; onClick: () => void }) {
  const laneColor = LANE_COLORS[role.lane] ?? '#888'
  const grade = role.fit_grade ?? '?'
  const gradeColor = GRADE_COLORS[grade] ?? '#888'
  const age = ageLabel(role.posted_at)
  const stale = age === 'stale'
  const stage = role.score_stage2 != null ? 'S2' : 'S1'

  return (
    <div
      onClick={onClick}
      className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 cursor-pointer hover:border-zinc-600 transition-colors select-none"
    >
      <div className="flex items-start gap-2">
        {/* Company logo placeholder */}
        <div
          className="w-8 h-8 rounded-md flex items-center justify-center text-xs font-bold shrink-0"
          style={{ backgroundColor: hashColor(role.company ?? '') }}
        >
          {companyInitials(role.company ?? '?')}
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-sm text-white font-medium truncate">{role.title}</div>
          <div className="text-xs text-zinc-400 truncate">{role.company}</div>
        </div>

        {/* Grade circle */}
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
          style={{ backgroundColor: gradeColor + '22', border: `1.5px solid ${gradeColor}`, color: gradeColor }}
        >
          {grade}
        </div>
      </div>

      <div className="flex items-center gap-1.5 mt-2 flex-wrap">
        {/* Lane badge */}
        <span
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
        {role.comp_min && (
          <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-900/30 text-emerald-400 font-mono">
            ${Math.round(role.comp_min / 1000)}K{role.comp_max ? `–$${Math.round(role.comp_max / 1000)}K` : '+'}
          </span>
        )}

        {/* Stage badge */}
        <span className={`text-xs px-1 py-0.5 rounded font-mono ml-auto ${stage === 'S2' ? 'text-cyan-400' : 'text-zinc-600'}`}>
          [{stage}]
        </span>
      </div>
    </div>
  )
}
