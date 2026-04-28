'use client'
import { useEffect, useState } from 'react'
import type { Offer } from './types'

function formatK(n: number | null | undefined) {
  if (!n) return '—'
  return `$${Math.round(n / 1000)}K`
}

export function OfertasView() {
  const [offers, setOffers] = useState<Offer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ac = new AbortController()
    fetch('/api/coin/offers', { signal: ac.signal })
      .then(async r => {
        if (!r.ok) throw new Error(`Offers API returned ${r.status}`)
        const data = await r.json()
        return Array.isArray(data) ? data : []
      })
      .then(setOffers)
      .catch(e => {
        if (e?.name !== 'AbortError') setError('Could not load offers.')
      })
      .finally(() => { if (!ac.signal.aborted) setLoading(false) })
    return () => ac.abort()
  }, [])

  if (loading) return <div className="text-zinc-400 text-sm">Loading offers…</div>
  if (error) {
    return (
      <div role="alert" className="text-sm text-red-400 bg-red-950/30 border border-red-900/50 rounded p-3">
        {error}
      </div>
    )
  }

  if (offers.length === 0) {
    return (
      <div className="text-center py-12 text-zinc-400">
        <div className="text-4xl mb-3" aria-hidden="true">💰</div>
        <div className="text-sm">No offers yet.</div>
        <div className="text-xs mt-1 text-zinc-500">
          Run <code className="text-violet-400">/coin ofertas</code> in Claude to compare when you get one.
        </div>
      </div>
    )
  }

  const active = offers.filter(o => o.status === 'active')
  const anchors = offers.filter(o => o.status === 'market_anchor')

  return (
    <div className="overflow-x-auto">
      <div className="flex gap-4 min-w-max">
        {[...active, ...anchors].slice(0, 4).map(offer => (
          <div key={offer.id} className="w-56 bg-zinc-900 border border-zinc-800 rounded-xl p-4">
            <div className="text-xs text-zinc-400 mb-1">{offer.status === 'market_anchor' ? 'Market Anchor' : 'Active Offer'}</div>
            <div className="text-white font-semibold">{offer.company}</div>
            <div className="text-zinc-400 text-sm truncate mb-3">{offer.title}</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-zinc-400">Base</span>
                <span className="text-white font-mono tabular-nums">{formatK(offer.base_salary)}</span>
              </div>
              {offer.rsu_total_value ? (
                <div className="flex justify-between">
                  <span className="text-zinc-400">RSU (4yr)</span>
                  <span className="text-white font-mono tabular-nums">{formatK(offer.rsu_total_value)}</span>
                </div>
              ) : null}
              {offer.signing_bonus ? (
                <div className="flex justify-between">
                  <span className="text-zinc-400">Signing</span>
                  <span className="text-white font-mono tabular-nums">{formatK(offer.signing_bonus)}</span>
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
