'use client'
import { useEffect, useState } from 'react'
import type { Outreach } from './types'

export function NetworkView() {
  const [outreach, setOutreach] = useState<Outreach[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ac = new AbortController()
    fetch('/api/coin/outreach', { signal: ac.signal })
      .then(async r => {
        if (!r.ok) {
          // 404 means the endpoint isn't implemented yet — treat as empty.
          if (r.status === 404) return []
          throw new Error(`Outreach API returned ${r.status}`)
        }
        const data = await r.json()
        return Array.isArray(data) ? data : []
      })
      .then(setOutreach)
      .catch(e => {
        if (e?.name !== 'AbortError') setError('Could not load outreach drafts.')
      })
      .finally(() => { if (!ac.signal.aborted) setLoading(false) })
    return () => ac.abort()
  }, [])

  const unsent = outreach.filter(o => !o.sent_at)

  if (loading) return <div className="text-zinc-400 text-sm">Loading network…</div>
  if (error) {
    return (
      <div role="alert" className="text-sm text-red-400 bg-red-950/30 border border-red-900/50 rounded p-3">
        {error}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-3">
          Outreach Drafts ({unsent.length} unsent)
        </h3>
        {unsent.length === 0 ? (
          <div className="text-zinc-400 text-sm">
            No unsent drafts. Run <code className="text-violet-400">/coin network-scan</code> in Claude to generate warm intros.
          </div>
        ) : (
          <div className="space-y-2">
            {unsent.map(o => (
              <div key={o.id} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-white">{o.recipient_name}</span>
                  <span className="text-xs text-zinc-400">{o.channel}</span>
                </div>
                <div className="text-xs text-zinc-400 truncate break-words">{o.draft?.slice(0, 120)}…</div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
