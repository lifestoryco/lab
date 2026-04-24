import type { Metadata } from "next";
import ShrinePage from "@/components/lab/shrine/ShrinePage";

export const metadata: Metadata = {
  title: "The Shrine — Sean's Lab",
  description:
    "A contemplative archive of deceased Buddhist masters. One ensō, one lineage, one breath.",
  alternates: { canonical: "https://www.handoffpack.com/lab/shrine" },
  openGraph: {
    title: "The Shrine",
    description:
      "A contemplative archive of deceased Buddhist masters. One ensō, one lineage, one breath.",
    type: "website",
    url: "https://www.handoffpack.com/lab/shrine",
  },
};

export default function ShrineRoute() {
  return <ShrinePage />;
}
