import type { MetadataRoute } from 'next';

import { absoluteUrl, siteIndexable } from '@/lib/site';

export default function robots(): MetadataRoute.Robots {
  // Let crawlers read noindex on HTML pages. API access still requires auth.
  const searchRules = { allow: '/', disallow: ['/api', '/health'] };
  return {
    rules: [
      { userAgent: '*', ...searchRules },
      { userAgent: 'OAI-SearchBot', ...searchRules },
    ],
    ...(siteIndexable ? { sitemap: absoluteUrl('/sitemap.xml') } : {}),
  };
}
