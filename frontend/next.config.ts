import type { NextConfig } from 'next';

const backendOrigin = process.env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8101';
const isDevelopment = process.env.NODE_ENV === 'development';

const nextConfig: NextConfig = {
  agentRules: false,
  skipTrailingSlashRedirect: true,
  trailingSlash: true,
  images: {
    unoptimized: true,
    remotePatterns: [
      { protocol: 'http', hostname: '**' },
      { protocol: 'https', hostname: '**' },
    ],
  },
  ...(isDevelopment
    ? {
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
      }
    : { output: 'export' }),
};

export default nextConfig;
