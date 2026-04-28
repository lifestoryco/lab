'use client'
import type { ScoreBreakdown } from './types'

const DIMENSION_LABELS: Record<string, string> = {
  comp: 'Comp',
  company_tier: 'Co. Tier',
  skill_match: 'Skills',
  title_match: 'Title',
  remote: 'Remote',
  seniority_fit: 'Seniority',
  freshness: 'Freshness',
  application_effort: 'Effort',
  culture_fit: 'Culture',
}

export function ScoreChart({ breakdown }: { breakdown: ScoreBreakdown }) {
  const { composite, grade, dimensions } = breakdown
  const gradeColor = { A: '#22c55e', B: '#86efac', C: '#facc15', D: '#f97316', F: '#ef4444' }[grade] ?? '#888'

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 mb-4">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold font-mono"
          style={{ backgroundColor: gradeColor + '22', border: `2px solid ${gradeColor}`, color: gradeColor }}
        >
          {grade}
        </div>
        <div>
          <div className="text-2xl font-mono font-bold text-white">{composite.toFixed(1)}</div>
          <div className="text-xs text-zinc-400">composite score</div>
        </div>
      </div>

      {Object.entries(dimensions).map(([key, dim]) => {
        if (key === 'domain_fit') return null
        const label = DIMENSION_LABELS[key] ?? key
        const pct = Math.min(100, dim.raw)
        const color = pct >= 70 ? '#22c55e' : pct >= 40 ? '#facc15' : '#ef4444'
        return (
          <div key={key} className="flex items-center gap-2 text-sm">
            <div className="w-20 text-zinc-400 text-right shrink-0">{label}</div>
            <div className="flex-1 bg-zinc-800 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
            <div className="w-8 text-right font-mono text-xs text-zinc-300">{dim.raw.toFixed(0)}</div>
          </div>
        )
      })}
    </div>
  )
}
