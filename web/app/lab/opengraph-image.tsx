import { ImageResponse } from 'next/og'
import { OGCard, OG_SIZE, OG_CONTENT_TYPE } from '@/components/lab/og-card'

export const runtime = 'edge'
export const size = OG_SIZE
export const contentType = OG_CONTENT_TYPE
export const alt = 'Sean Ivins\' Lab — Experiments in generative art and interactive systems'

export default async function Image() {
  return new ImageResponse(
    (
      <OGCard
        badge="Lab"
        name="LAB"
        tagline="Experiments in generative art and interactive systems."
        url="handoffpack.com/lab"
        gradient="linear-gradient(135deg, #050505 0%, #1a1a1a 50%, #2a2a2a 100%)"
        accent="#e2e2e2"
      />
    ),
    { ...size }
  )
}
