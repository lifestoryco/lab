// Architecture: mirrors /lab/holo pattern.
// Read path: better-sqlite3 via server.ts (zero-latency SSR).
// Mutation path: subprocess to careerops.web_cli (business logic stays in Python).

import type { Metadata } from 'next'
import { CoinPage } from '@/components/lab/coin/CoinPage'
import { fetchDashboard } from '@/components/lab/coin/server'

export const metadata: Metadata = {
  title: 'Coin — Career Ops',
  description: 'Sean Ivins career pipeline — discover, score, tailor, track.',
}

export default async function Page() {
  let initial = null
  try {
    initial = await fetchDashboard()
  } catch {
    // DB not available in this environment — client will load via API
  }
  return <CoinPage initialData={initial} />
}
