'use client'
import { useState, useEffect } from 'react'
import type { Outreach } from './types'

export function NetworkView() {
  const [outreach, setOutreach] = useState<Outreach[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/coin/outreach').then(r => r.json()).then(setOutreach).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const unsent = outreach.filter(o => !o.sent_at)

  if (loading) return <div className="text-zinc-500 text-sm">Loading network…</div>

  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
          Outreach Drafts ({unsent.length} unsent)
        </h3>
        {unsent.length === 0 ? (
          <div className="text-zinc-600 text-sm">No unsent drafts. Run <code className="text-violet-400">/coin network-scan</code> in Claude to generate warm intros.</div>
        ) : (
          <div className="space-y-2">
            {unsent.map(o => (
              <div key={o.id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">{o.recipient_name}</span>
                  <span className="text-xs text-zinc-500">{o.channel}</span>
                </div>
                <div className="text-xs text-zinc-400 truncate">{o.draft?.slice(0, 120)}…</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
