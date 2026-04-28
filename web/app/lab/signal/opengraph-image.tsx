import { ImageResponse } from 'next/og'
import { OGCard, OG_SIZE, OG_CONTENT_TYPE } from '@/components/lab/og-card'

export const runtime = 'edge'
export const size = OG_SIZE
export const contentType = OG_CONTENT_TYPE
export const alt = 'SIGNAL — Build worlds that play themselves.'

export default async function Image() {
  return new ImageResponse(
    (
      <OGCard
        badge="signal"
        name="SIGNAL"
        tagline="Build worlds that play themselves."
        url="handoffpack.com/lab/signal"
        gradient="linear-gradient(145deg, #000000 0%, #333333 35%, #666666 65%, #ffffff 100%)"
        accent="#888888"
      />
    ),
    { ...size }
  )
}
