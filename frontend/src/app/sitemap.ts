import type { MetadataRoute } from 'next';

import { absoluteUrl, siteIndexable } from '@/lib/site';

export default function sitemap(): MetadataRoute.Sitemap {
  return siteIndexable
    ? ['/', '/guide/'].map((path) => ({ url: absoluteUrl(path) }))
    : [];
}
