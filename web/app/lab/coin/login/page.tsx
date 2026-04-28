'use client'
import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Lock } from 'lucide-react'

function LoginForm() {
  const router = useRouter()
  const params = useSearchParams()
  const next = params.get('next') || '/lab/coin'

  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const r = await fetch('/api/coin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (!r.ok) {
        setError('Wrong password.')
        setSubmitting(false)
        return
      }
      router.push(next)
      router.refresh()
    } catch {
      setError('Something went wrong. Try again.')
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4">
      <div className="flex items-center gap-2 text-violet-400">
        <Lock size={18} />
        <span className="text-sm font-mono tracking-wider">COIN</span>
      </div>
      <div>
        <div className="text-white font-semibold">Career Ops — Private</div>
        <div className="text-zinc-500 text-xs mt-1">Enter the password to continue.</div>
      </div>
      <label htmlFor="coin-password" className="sr-only">Password</label>
      <input
        id="coin-password"
        type="password"
        autoFocus
        autoComplete="current-password"
        value={password}
        onChange={e => setPassword(e.target.value)}
        placeholder="Password"
        aria-label="Password"
        className="w-full min-h-[44px] bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/30"
      />
      {error && <div className="text-xs text-red-400">{error}</div>}
      <button
        type="submit"
        disabled={submitting || !password}
        className="w-full min-h-[44px] py-2 rounded-lg text-sm font-medium bg-violet-900/50 hover:bg-violet-900 text-violet-200 disabled:opacity-50 transition-colors"
      >
        {submitting ? 'Checking…' : 'Unlock'}
      </button>
    </form>
  )
}

export default function CoinLogin() {
  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
      <Suspense fallback={<div className="text-zinc-500 text-sm">Loading…</div>}>
        <LoginForm />
      </Suspense>
    </div>
  )
}
