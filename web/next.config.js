/** @type {import('next').NextConfig} */
//
// assetPrefix — required when this app is served via a rewrite from a different
// origin (handoffpack-www proxies /lab/* and /api/coin/* here). Without it, the
// browser requests /_next/static/* from www.handoffpack.com (404), and the page
// renders unstyled because Tailwind/JS chunks never load. Setting assetPrefix
// to the canonical lab origin makes the SSR'd HTML emit absolute asset URLs
// pointing back to lab-lifestoryco.vercel.app, which serves them directly.
//
// Set LAB_PUBLIC_URL=https://lab-lifestoryco.vercel.app on the lab-lifestoryco
// Vercel production env. Local dev leaves it unset → relative paths still work.
//
// Note: handoffpack-www's CSP must whitelist this origin (script-src/style-src/
// font-src/img-src/connect-src) or the browser will block the cross-origin
// assets. See lab/CLAUDE.md "Two-repo deployment topology" for the full story.
const assetPrefix = process.env.LAB_PUBLIC_URL
  ? process.env.LAB_PUBLIC_URL.replace(/\/$/, '')
  : undefined;

const nextConfig = {
  reactStrictMode: true,
  ...(assetPrefix ? { assetPrefix } : {}),
  experimental: {
    // better-sqlite3 is a native .node module — exclude from webpack bundling
    serverComponentsExternalPackages: ['better-sqlite3'],
    // Bundle the COIN read-only DB snapshot into serverless function output
    // so /lab/coin and /api/coin/* can find it at runtime on Vercel.
    outputFileTracingIncludes: {
      '/api/coin/**/*': ['./data/coin/**/*'],
      '/lab/coin/**/*': ['./data/coin/**/*'],
    },
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "commons.wikimedia.org" },
      { protocol: "https", hostname: "upload.wikimedia.org" },
    ],
  },
  async redirects() {
    return [
      { source: "/", destination: "/lab", permanent: false },
    ];
  },
};

module.exports = nextConfig;
