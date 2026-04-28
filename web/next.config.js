/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
