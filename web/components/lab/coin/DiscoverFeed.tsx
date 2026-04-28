'use client'
import { useEffect, useState } from 'react'
import type { Role } from './types'
import { RoleCard } from './RoleCard'
import { RoleDetail } from './RoleDetail'
import { LANES, gradeForScore } from './constants'

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
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    const ac = new AbortController()
    fetch(`/api/coin/roles?limit=50${lane ? `&lane=${lane}` : ''}`, { signal: ac.signal })
      .then(r => r.json())
      .then((all: Role[]) => {
        if (ac.signal.aborted) return
        const list = Array.isArray(all) ? all : []
        const cutoff = days === 'all' ? null : Date.now() - Number(days) * 86400000
        const filtered = list.filter(r => {
          if (!cutoff) return true
          const d = r.discovered_at ? new Date(r.discovered_at).getTime() : 0
          return d >= cutoff
        })
        setRoles(filtered.map(r => ({ ...r, fit_grade: gradeForScore(r.fit_score) })))
      })
      .catch(e => {
        if (e?.name !== 'AbortError') setError('Could not load roles. Try again.')
      })
      .finally(() => { if (!ac.signal.aborted) setLoading(false) })
    return () => ac.abort()
  }, [lane, days])

  return (
    <div>
      <div className="flex gap-2 mb-4 flex-wrap">
        <label className="sr-only" htmlFor="discover-lane">Filter by lane</label>
        <select
          id="discover-lane"
          value={lane}
          onChange={e => setLane(e.target.value)}
          className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-white min-h-[36px]"
        >
          <option value="">All lanes</option>
          {LANES.map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <label className="sr-only" htmlFor="discover-days">Filter by recency</label>
        <select
          id="discover-days"
          value={days}
          onChange={e => setDays(e.target.value)}
          className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-white min-h-[36px]"
        >
          <option value="7">Last 7 days</option>
          <option value="14">Last 14 days</option>
          <option value="30">Last 30 days</option>
          <option value="all">All time</option>
        </select>
        <span aria-live="polite" className="text-zinc-400 text-sm self-center tabular-nums">
          {loading ? '…' : `${roles.length} roles`}
        </span>
      </div>
      {error ? (
        <div role="alert" className="text-sm text-red-400 bg-red-950/30 border border-red-900/50 rounded p-3">
          {error}
        </div>
      ) : loading ? (
        <div className="text-zinc-400 text-sm">Loading…</div>
      ) : roles.length === 0 ? (
        <div className="text-zinc-400 text-sm">No roles match this filter.</div>
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
