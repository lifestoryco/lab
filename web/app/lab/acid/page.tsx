import type { Metadata } from 'next'
import AcidGalleryPage from '@/components/lab/acid/AcidGalleryPage'

export const metadata: Metadata = {
  title: 'ACID — Sean\'s Lab',
  description: '22 living formulas rendered in ASCII light.',
}

export default function AcidRoute() {
  return <AcidGalleryPage />
}
