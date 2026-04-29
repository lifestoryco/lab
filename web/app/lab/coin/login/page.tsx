'use client'
import { useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { Lock, Mail } from 'lucide-react'
import { createSupabaseBrowserClient } from '@/lib/supabase/client'

// Magic-link login. Replaces the prior shared-password gate. The auth flow:
//   1. User enters email → supabase.auth.signInWithOtp emails them a link
//   2. Link goes to /auth/callback?code=… on this domain
//   3. /auth/callback exchanges the code for a session cookie + redirects
//      back to the original ?next= path
//
// First user to log in becomes the de-facto owner (Sean). Inviting others is
// just sharing the login URL; their data is RLS-isolated automatically.

function LoginForm() {
  const params = useSearchParams()
  const next = params.get('next') || '/lab/coin'

  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const supabase = createSupabaseBrowserClient()
      // emailRedirectTo must be on this origin so the cookie set on /auth/callback
      // is visible to the COIN dashboard. The ?next= survives via the redirect URL.
      const redirectTo = `${window.location.origin}/auth/callback?next=${encodeURIComponent(next)}`
      const { error: err } = await supabase.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: redirectTo },
      })
      if (err) {
        setError(err.message)
        setSubmitting(false)
        return
      }
      setSent(true)
      setSubmitting(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Try again.')
      setSubmitting(false)
    }
  }

  if (sent) {
    return (
      <div className="w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2 text-emerald-400">
          <Mail size={18} aria-hidden="true" />
          <span className="text-sm font-mono tracking-wider">CHECK YOUR EMAIL</span>
        </div>
        <div className="text-white text-sm leading-relaxed">
          A sign-in link is on its way to <span className="font-mono text-emerald-300">{email}</span>.
          Click it to finish signing in.
        </div>
        <button
          onClick={() => { setSent(false); setEmail(''); setError(null) }}
          className="text-xs text-zinc-400 hover:text-white"
        >
          Use a different email
        </button>
      </div>
    )
  }

  return (
    <form onSubmit={onSubmit} className="w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4">
      <div className="flex items-center gap-2 text-violet-400">
        <Lock size={18} aria-hidden="true" />
        <span className="text-sm font-mono tracking-wider">COIN</span>
      </div>
      <div>
        <div className="text-white font-semibold">Career Ops — Private</div>
        <div className="text-zinc-500 text-xs mt-1">Enter your email; we&apos;ll send you a sign-in link.</div>
      </div>
      <label htmlFor="coin-email" className="sr-only">Email</label>
      <input
        id="coin-email"
        type="email"
        autoFocus
        autoComplete="email"
        required
        value={email}
        onChange={e => setEmail(e.target.value)}
        placeholder="you@example.com"
        aria-label="Email"
        className="w-full min-h-[44px] bg-zinc-900 border border-zinc-700 rounded px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-violet-500 focus:ring-2 focus:ring-violet-500/30"
      />
      {error && <div className="text-xs text-red-400">{error}</div>}
      <button
        type="submit"
        disabled={submitting || !email}
        className="w-full min-h-[44px] py-2 rounded-lg text-sm font-medium bg-violet-900/50 hover:bg-violet-900 text-violet-200 disabled:opacity-50 transition-colors"
      >
        {submitting ? 'Sending…' : 'Send sign-in link'}
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
