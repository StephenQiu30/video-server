import type { NextConfig } from 'next';

const backendOrigin = process.env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8111';

const nextConfig: NextConfig = {
  agentRules: false,
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
