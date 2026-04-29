// Supabase magic-link callback handler.
//
// The user clicks the link in their email; Supabase appends ?code=… to this
// route. We exchange the code for a session via the SSR client (which sets
// the auth cookies on the response), then 302 to the originally-requested
// page. If anything goes wrong, we land back on /lab/coin/login with an error.

import { NextRequest, NextResponse } from 'next/server'
import { createSupabaseServerClient } from '@/lib/supabase/server'

export async function GET(req: NextRequest) {
  const url = req.nextUrl
  const code = url.searchParams.get('code')
  const next = url.searchParams.get('next') ?? '/lab/coin'
  // Belt-and-suspenders: only accept relative redirects on this origin so a
  // crafted ?next=https://attacker.example.com link can't bounce a logged-in
  // user away with their session cookie still warm.
  const safeNext = next.startsWith('/') && !next.startsWith('//') ? next : '/lab/coin'

  if (!code) {
    const dest = url.clone()
    dest.pathname = '/lab/coin/login'
    dest.search = '?error=missing_code'
    return NextResponse.redirect(dest)
  }

  const supabase = await createSupabaseServerClient()
  const { error } = await supabase.auth.exchangeCodeForSession(code)
  if (error) {
    const dest = url.clone()
    dest.pathname = '/lab/coin/login'
    dest.search = `?error=${encodeURIComponent(error.message)}`
    return NextResponse.redirect(dest)
  }

  const dest = url.clone()
  dest.pathname = safeNext
  dest.search = ''
  return NextResponse.redirect(dest)
}
