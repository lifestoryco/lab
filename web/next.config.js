/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // better-sqlite3 is a native .node module — exclude from webpack bundling
  experimental: {
    serverComponentsExternalPackages: ['better-sqlite3'],
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
  async rewrites() {
    return [
      // /lab/coy → static santos-coy-legacy site served from /public/lab/coy
      { source: "/lab/coy", destination: "/lab/coy/index.html" },
      { source: "/lab/coy/people/:slug", destination: "/lab/coy/people/:slug.html" },
    ];
  },
};

module.exports = nextConfig;
