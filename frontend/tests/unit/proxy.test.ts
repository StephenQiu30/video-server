import { NextRequest } from 'next/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { proxy } from '@/proxy';

describe('frontend proxy', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('preserves the requested origin when a canonical site URL is configured', () => {
    vi.stubEnv('APP_ENV', 'production');
    vi.stubEnv('SITE_URL', 'https://stephenqius-macbook-pro.tailda4efa.ts.net');

    const response = proxy(
      new NextRequest('http://127.0.0.1:8101/user/login?redirect=%2Fhistory'),
    );

    expect(response.status).toBe(200);
    expect(response.headers.get('location')).toBeNull();
  });
});
