'use client'

import { Component, type ReactNode } from 'react'
import SceneFallback from './SceneFallback'

interface Props { children: ReactNode }
interface State { hasError: boolean }

export default class SceneErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(err: unknown) {
    // Swallow — surface as fallback UI instead of crashing the page.
    // eslint-disable-next-line no-console
    console.warn('[Signal] Scene error:', err)
  }

  render() {
    if (this.state.hasError) return <SceneFallback />
    return this.props.children
  }
}
