'use client'
import { createBrowserClient } from '@supabase/ssr'
import type { Database } from '@/components/lab/coin/supabase-types'

let _client: ReturnType<typeof createBrowserClient<Database>> | null = null

// Browser-side Supabase client. Singleton so we don't open multiple websocket
// channels per page. Use from Client Components only.
export function createSupabaseBrowserClient() {
  if (_client) return _client
  _client = createBrowserClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
  return _client
}
