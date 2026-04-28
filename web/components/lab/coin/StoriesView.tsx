'use client'
import { useEffect, useState } from 'react'

export function StoriesView() {
  const [raw, setRaw] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ac = new AbortController()
    fetch('/api/coin/stories', { signal: ac.signal })
      .then(async r => {
        if (!r.ok) {
          if (r.status === 404) return ''
          throw new Error(`Stories API returned ${r.status}`)
        }
        return r.text()
      })
      .then(t => setRaw(t.trim() || null))
      .catch(e => {
        if (e?.name !== 'AbortError') setError('Could not load stories.')
      })
      .finally(() => { if (!ac.signal.aborted) setLoading(false) })
    return () => ac.abort()
  }, [])

  if (loading) return <div className="text-zinc-400 text-sm">Loading stories…</div>
  if (error) {
    return (
      <div role="alert" className="text-sm text-red-400 bg-red-950/30 border border-red-900/50 rounded p-3">
        {error}
      </div>
    )
  }

  if (!raw) {
    return (
      <div className="text-center py-12 text-zinc-400">
        <div className="text-4xl mb-3" aria-hidden="true">📖</div>
        <div className="text-sm font-medium text-zinc-200">No stories captured yet.</div>
        <div className="text-xs mt-2 max-w-xs mx-auto text-zinc-400">
          Run <code className="text-violet-400">/coin deep-dive</code> in Claude to extract 30–50 career proof points from your experience.
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="text-xs text-zinc-400 uppercase tracking-wider mb-3">stories.yml</div>
      <pre className="text-xs text-zinc-200 bg-zinc-900 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap break-words max-h-[60vh]">
        {raw}
      </pre>
    </div>
  )
}
