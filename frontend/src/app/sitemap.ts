import type { MetadataRoute } from 'next';

import { absoluteUrl, publicPages, siteIndexable } from '@/lib/site';

export default function sitemap(): MetadataRoute.Sitemap {
  return siteIndexable
    ? publicPages.map(({ path }) => ({ url: absoluteUrl(path) }))
    : [];
}
