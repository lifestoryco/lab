// Thin PostHog wrapper for SIGNAL telemetry.
// Events never block the UI; failures are swallowed silently.

import posthog from 'posthog-js'

export type SignalEvent =
  | 'signal_entered'
  | 'signal_first_tap'
  | 'signal_first_chain'
  | 'signal_biome_complete'
  | 'signal_session_end'
  | 'signal_result_shared'
  | 'signal_shared_url_opened'
  // Cage Mode funnel
  | 'signal_cage_started'
  | 'signal_cage_solved'
  | 'signal_cage_escaped'

export function track(event: SignalEvent, props: Record<string, string | number | boolean> = {}) {
  if (typeof window === 'undefined') return
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if ((posthog as any).__loaded) posthog.capture(event, props)
  } catch {
    /* swallow */
  }
}
