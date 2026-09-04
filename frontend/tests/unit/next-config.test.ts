import { describe, expect, it } from 'vitest';

import nextConfig from '../../next.config';

describe('Next.js proxy configuration', () => {
  it('forwards API requests without redirecting POST bodies', async () => {
    expect(nextConfig.trailingSlash).toBe(true);
    expect(nextConfig.skipTrailingSlashRedirect).toBe(true);

    const rewrites = await nextConfig.rewrites?.();
    expect(rewrites).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          source: '/api/:path*',
        }),
      ]),
    );
  });
});
