'use client'
// Minimal cross-component state. Most COIN UI state lives locally in the
// components that own it; this store only holds the active tab so a page
// reload preserves it (zustand persists in memory across mounts).
import { create } from 'zustand'

export type Tab = 'pipeline' | 'discover' | 'roles' | 'network' | 'ofertas' | 'stories'

interface CoinStore {
  activeTab: Tab
  setTab: (t: Tab) => void
}

export const useCoinStore = create<CoinStore>((set) => ({
  activeTab: 'pipeline',
  setTab: (t) => set({ activeTab: t }),
}))
