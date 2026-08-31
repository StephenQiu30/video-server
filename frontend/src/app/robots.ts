import type { MetadataRoute } from 'next';

import { absoluteUrl, siteUrl } from '@/lib/site';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/health/'],
    },
    sitemap: absoluteUrl('/sitemap.xml'),
    host: siteUrl.origin,
  };
}
