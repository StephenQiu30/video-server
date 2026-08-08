import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  agentRules: false,
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: 'http', hostname: '**' },
      { protocol: 'https', hostname: '**' },
    ],
  },
  ...(process.env.NODE_ENV === 'development'
    ? {
        async rewrites() {
          return [
            {
              source: '/api/:path*',
              destination: 'http://127.0.0.1:8101/api/:path*',
            },
            {
              source: '/health/:path*',
              destination: 'http://127.0.0.1:8101/health/:path*',
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
