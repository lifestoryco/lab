import { NextResponse, type NextRequest } from 'next/server'
import { updateSupabaseSession } from '@/lib/supabase/middleware'

// Gate /lab/coin and /api/coin/* behind Supabase Auth. The /lab/coin/login
// page and the magic-link callback are always accessible.
//
// Replaces the prior coin_auth=COIN_WEB_PASSWORD cookie scheme. Multi-user
// from day one: the user's identity comes from the Supabase session, not a
// shared password.

const PUBLIC_PATHS = new Set([
  '/lab/coin/login',
  '/auth/callback',
])

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Refresh the session cookie regardless — keeps users logged in across tabs.
  const { response, user } = await updateSupabaseSession(req)

  if (PUBLIC_PATHS.has(pathname)) return response
  if (user) return response

  // API: 401 JSON so the client can handle gracefully without a redirect chain.
  if (pathname.startsWith('/api/coin')) {
    return NextResponse.json(
      { error: 'Unauthorized' },
      { status: 401, headers: { 'Cache-Control': 'private, no-store' } }
    )
  }

  // Page: redirect to login with return path so the magic-link click lands
  // back where the user started.
  const url = req.nextUrl.clone()
  url.pathname = '/lab/coin/login'
  url.searchParams.set('next', pathname + req.nextUrl.search)
  return NextResponse.redirect(url)
}

export const config = {
  // Run on /auth/callback too so the magic-link cookie gets set before the
  // /lab/coin redirect. (Note: /auth/callback is in PUBLIC_PATHS above; this
  // only ensures the middleware runs to set cookies.)
  matcher: ['/lab/coin/:path*', '/api/coin/:path*', '/auth/callback'],
}
