import type { Metadata } from 'next'
import LabGallery from '@/components/lab/LabGallery'

export const metadata: Metadata = {
  title: 'Lab — Sean Ivins',
  description: 'Experiments in generative art and interactive systems.',
}

export default function LabRoute() {
  return <LabGallery />
}
