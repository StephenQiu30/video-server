import type { MetadataRoute } from 'next';

import { siteConfig, socialPalette } from '@/lib/site';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: siteConfig.name,
    short_name: siteConfig.shortName,
    description: siteConfig.description,
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: socialPalette.foreground,
    theme_color: socialPalette.background,
    lang: 'zh-CN',
    categories: ['productivity', 'utilities', 'multimedia'],
    icons: [
      {
        src: '/logo.png',
        sizes: '1024x1024',
        type: 'image/png',
        purpose: 'maskable',
      },
      {
        src: '/logo.svg',
        sizes: 'any',
        type: 'image/svg+xml',
        purpose: 'any',
      },
    ],
  };
}
