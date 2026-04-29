// Architecture: per-user data via Supabase. SSR fetches the user's dashboard
// using the request-scoped Supabase client (RLS does the isolation). Mutations
// go through /api/coin/[...slug] (also RLS-scoped, no Python subprocess).

import { Suspense } from 'react'
import type { Metadata } from 'next'
import { CoinPage } from '@/components/lab/coin/CoinPage'
import { fetchDashboard } from '@/components/lab/coin/server'

export const metadata: Metadata = {
  title: 'Coin — Career Ops',
  description: 'Sean Ivins career pipeline — discover, score, tailor, track.',
}

// Per-user, auth-gated, depends on cookies. No reason to prerender.
export const dynamic = 'force-dynamic'

export default async function Page() {
  let initial = null
  try {
    initial = await fetchDashboard()
  } catch {
    // DB not available in this environment — client will load via API
  }
  // CoinPage uses useSearchParams (URL-state for tab/role) which Next requires
  // to live under a Suspense boundary. The fallback only renders during the
  // brief client hydration window before the auth cookie is read.
  return (
    <Suspense fallback={<div className="min-h-screen bg-black text-zinc-500 text-sm flex items-center justify-center">Loading…</div>}>
      <CoinPage initialData={initial} />
    </Suspense>
  )
}
