'use client'
// URL-driven state. Encoding tab + selected-role-id into the query string
// means the browser back/forward buttons stay inside COIN instead of
// punting users back to the lab gallery, and a copied URL deep-links
// straight to the right view.
//
// Implementation: useSearchParams to read, router.replace/push to write.
// We use replace (not push) for tab switches so a long browsing session
// doesn't leave 50 useless history entries — but we DO push for opening
// a role detail dialog, since "back closes the modal" is the expected
// pattern users learn from native apps.

import { useRouter, useSearchParams } from 'next/navigation'
import { useCallback } from 'react'

export type Tab = 'pipeline' | 'discover' | 'roles' | 'network' | 'ofertas' | 'stories'
const VALID_TABS: ReadonlySet<Tab> = new Set<Tab>([
  'pipeline','discover','roles','network','ofertas','stories'
])

export function useCoinUrlState() {
  const router = useRouter()
  const params = useSearchParams()

  const raw = params.get('tab')
  const tab: Tab = raw && VALID_TABS.has(raw as Tab) ? (raw as Tab) : 'pipeline'

  const rawRole = params.get('role')
  const roleNum = rawRole != null ? Number(rawRole) : NaN
  const roleId: number | null =
    Number.isFinite(roleNum) && Number.isInteger(roleNum) && roleNum > 0 ? roleNum : null

  const writeParams = useCallback(
    (mut: (sp: URLSearchParams) => void, mode: 'replace' | 'push' = 'replace') => {
      const sp = new URLSearchParams(params.toString())
      mut(sp)
      const qs = sp.toString()
      const url = qs ? `?${qs}` : window.location.pathname
      if (mode === 'push') router.push(url)
      else router.replace(url)
    },
    [router, params]
  )

  const setTab = useCallback((next: Tab) => {
    writeParams(sp => {
      if (next === 'pipeline') sp.delete('tab')        // pipeline is the default
      else sp.set('tab', next)
      sp.delete('role')                                // tab change closes any open detail
    }, 'replace')
  }, [writeParams])

  const setRoleId = useCallback((next: number | null) => {
    writeParams(sp => {
      if (next == null) sp.delete('role')
      else sp.set('role', String(next))
    }, 'push')
  }, [writeParams])

  return { tab, setTab, roleId, setRoleId }
}
