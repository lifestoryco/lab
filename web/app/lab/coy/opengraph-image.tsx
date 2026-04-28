import { ImageResponse } from 'next/og'
import { OGCard, OG_SIZE, OG_CONTENT_TYPE } from '@/components/lab/og-card'

export const runtime = 'edge'
export const size = OG_SIZE
export const contentType = OG_CONTENT_TYPE
export const alt = 'The Santos Coy Legacy — sixteen generations from Lepe to Houston.'

export default async function Image() {
  return new ImageResponse(
    (
      <OGCard
        badge="coy"
        name="SANTOS COY"
        tagline="Blood, frontier, and the making of Texas. Sixteen generations from Lepe, Spain to Houston."
        url="handoffpack.com/lab/coy"
        gradient="linear-gradient(145deg, #1c1a17 0%, #2a2723 30%, #704214 65%, #c9a961 100%)"
        accent="#c9a961"
      />
    ),
    { ...size }
  )
}
