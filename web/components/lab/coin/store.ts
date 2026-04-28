'use client'
import { create } from 'zustand'
import type { DashboardData, Role } from './types'

type Tab = 'pipeline' | 'discover' | 'roles' | 'network' | 'ofertas' | 'stories'

interface CoinStore {
  activeTab: Tab
  setTab: (t: Tab) => void
  selectedRole: Role | null
  setSelectedRole: (r: Role | null) => void
  dashboard: DashboardData | null
  setDashboard: (d: DashboardData) => void
  loading: boolean
  setLoading: (v: boolean) => void
}

export const useCoinStore = create<CoinStore>((set) => ({
  activeTab: 'pipeline',
  setTab: (t) => set({ activeTab: t }),
  selectedRole: null,
  setSelectedRole: (r) => set({ selectedRole: r }),
  dashboard: null,
  setDashboard: (d) => set({ dashboard: d }),
  loading: false,
  setLoading: (v) => set({ loading: v }),
}))
