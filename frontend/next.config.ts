import type { NextConfig } from 'next';

const backendOrigin = process.env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8111';

const nextConfig: NextConfig = {
  agentRules: false,
  poweredByHeader: false,
  // API routes are forwarded to FastAPI without a trailing slash. Disabling
  // Next's global redirect preserves POST bodies across every browser,
  // including Safari/WebKit.
  skipTrailingSlashRedirect: true,
  trailingSlash: true,
  output: 'standalone',
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: 'http', hostname: '**' },
      { protocol: 'https', hostname: '**' },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${backendOrigin}/api/:path*`,
      },
      {
        source: '/health/:path*',
        destination: `${backendOrigin}/health/:path*`,
      },
    ];
  },
};

export default nextConfig;
