import { describe, expect, it } from 'vitest';

import nextConfig from '../../next.config';

describe('Next.js proxy configuration', () => {
  it('does not bake a deployment-specific backend into build-time rewrites', () => {
    expect(nextConfig.trailingSlash).toBe(true);
    expect(nextConfig.skipTrailingSlashRedirect).toBe(true);

    expect(nextConfig.rewrites).toBeUndefined();
  });
});
