'use client'
import { useState, useEffect } from 'react'
import type { Role } from './types'
import { RoleCard } from './RoleCard'
import { RoleDetail } from './RoleDetail'

function gradeForRole(role: Role): string {
  const s = role.fit_score ?? 0
  if (s >= 85) return 'A'; if (s >= 70) return 'B'; if (s >= 55) return 'C'
  if (s >= 40) return 'D'; return 'F'
}

interface Props {
  onTrack: (id: number, status: string, note?: string) => void
  onTailor: (id: number) => void
  onNote: (id: number, text: string) => void
}

export function DiscoverFeed({ onTrack, onTailor, onNote }: Props) {
  const [roles, setRoles] = useState<Role[]>([])
  const [selected, setSelected] = useState<Role | null>(null)
  const [lane, setLane] = useState('')
  const [days, setDays] = useState('7')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/coin/roles?limit=50${lane ? `&lane=${lane}` : ''}`)
      .then(r => r.json())
      .then((all: Role[]) => {
        const cutoff = days === 'all' ? null : Date.now() - Number(days) * 86400000
        const filtered = all.filter(r => {
          if (!cutoff) return true
          const d = r.discovered_at ? new Date(r.discovered_at).getTime() : 0
          return d >= cutoff
        })
        setRoles(filtered.map(r => ({ ...r, fit_grade: gradeForRole(r) })))
      })
      .finally(() => setLoading(false))
  }, [lane, days])

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        <select
          value={lane} onChange={e => setLane(e.target.value)}
          className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-white"
        >
          <option value="">All lanes</option>
          {['mid-market-tpm','enterprise-sales-engineer','iot-solutions-architect','revenue-ops-operator'].map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <select
          value={days} onChange={e => setDays(e.target.value)}
          className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-white"
        >
          <option value="7">Last 7 days</option>
          <option value="14">Last 14 days</option>
          <option value="30">Last 30 days</option>
          <option value="all">All time</option>
        </select>
        <span className="text-zinc-500 text-sm self-center">{roles.length} roles</span>
      </div>
      {loading ? (
        <div className="text-zinc-500 text-sm">Loading…</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {roles.map(r => (
            <RoleCard key={r.id} role={r} onClick={() => setSelected(r)} />
          ))}
        </div>
      )}
      {selected && (
        <RoleDetail
          role={selected}
          onClose={() => setSelected(null)}
          onTrack={(status, note) => { onTrack(selected.id, status, note); setSelected(null) }}
          onTailor={() => onTailor(selected.id)}
          onNote={(text) => onNote(selected.id, text)}
        />
      )}
    </div>
  )
}
