import 'server-only'
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import type { Database } from '@/components/lab/coin/supabase-types'

// Server-side Supabase client bound to the user's request cookies. SSR pages,
// route handlers, and server actions should use this — RLS will then enforce
// per-user data isolation automatically.
//
// Do NOT call this from client components or middleware (use lib/supabase/client.ts
// or lib/supabase/middleware.ts respectively).

export async function createSupabaseServerClient() {
  const cookieStore = await cookies()
  return createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // Called from a Server Component — Next.js disallows mutation here.
            // The session refresh will happen on the next request via middleware.
          }
        },
      },
    }
  )
}

// Service-role client. Bypasses RLS — only use for trusted background jobs
// (e.g. data migration script). Never expose to client code.
export function createSupabaseServiceRoleClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY
  if (!url || !key) {
    throw new Error('SUPABASE_SERVICE_ROLE_KEY not configured')
  }
  // Use the standard JS client (not SSR) for service-role — no cookie story needed.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { createClient } = require('@supabase/supabase-js') as typeof import('@supabase/supabase-js')
  return createClient<Database>(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  })
}
