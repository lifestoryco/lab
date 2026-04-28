import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Gate /lab/coin and /api/coin/* behind COIN_WEB_PASSWORD.
// Login page at /lab/coin/login is always accessible.
// If no password is configured, the gate is open (useful for local dev).

export function middleware(req: NextRequest) {
  const pwd = process.env.COIN_WEB_PASSWORD
  if (!pwd) return NextResponse.next()

  const { pathname } = req.nextUrl

  // Always allow the login page itself and the login API
  if (pathname === '/lab/coin/login') return NextResponse.next()
  if (pathname === '/api/coin/login') return NextResponse.next()

  const cookie = req.cookies.get('coin_auth')?.value
  if (cookie === pwd) return NextResponse.next()

  // API: 401 JSON
  if (pathname.startsWith('/api/coin')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  // Page: redirect to login with return path
  const url = req.nextUrl.clone()
  url.pathname = '/lab/coin/login'
  url.searchParams.set('next', pathname)
  return NextResponse.redirect(url)
}

export const config = {
  matcher: ['/lab/coin/:path*', '/api/coin/:path*'],
}
