import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'
import type { Database } from '@/components/lab/coin/supabase-types'

// Middleware-side Supabase helper. Refreshes the auth session cookie if it has
// expired, then returns the user (or null). Designed to be called from
// middleware.ts before the route check.

export async function updateSupabaseSession(req: NextRequest) {
  let response = NextResponse.next({ request: req })

  const supabase = createServerClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return req.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => req.cookies.set(name, value))
          response = NextResponse.next({ request: req })
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // Touch getUser() so the SSR client refreshes any expiring tokens. This call
  // is what actually rotates the cookie; without it the user gets logged out
  // mid-session when the access token expires.
  const { data: { user } } = await supabase.auth.getUser()
  return { response, user }
}
