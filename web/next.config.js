/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
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
