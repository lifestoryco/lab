'use client'
import { useState, useEffect } from 'react'

export function StoriesView() {
  const [raw, setRaw] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/coin/stories')
      .then(r => r.text())
      .then(t => setRaw(t.trim() || null))
      .catch(() => setRaw(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-zinc-500 text-sm">Loading stories…</div>

  if (!raw) {
    return (
      <div className="text-center py-12 text-zinc-500">
        <div className="text-4xl mb-3">📖</div>
        <div className="text-sm font-medium text-zinc-300">No stories captured yet.</div>
        <div className="text-xs mt-2 max-w-xs mx-auto">
          Run <code className="text-violet-400">/coin deep-dive</code> in Claude to extract 30–50 career proof points from your experience.
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="text-xs text-zinc-500 uppercase tracking-wider mb-3">stories.yml</div>
      <pre className="text-xs text-zinc-300 bg-zinc-900 rounded-lg p-4 overflow-x-auto whitespace-pre-wrap max-h-[60vh]">
        {raw}
      </pre>
    </div>
  )
}
