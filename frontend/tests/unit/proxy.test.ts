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

  it('reads the backend origin at request time and preserves POSTs and queries', async () => {
    const request = new NextRequest(
      'http://localhost:8137/api/inspections?source=a%2Fb',
      { method: 'POST', body: '{"source":{"kind":"public_url"}}' },
    );
    for (const origin of ['http://first-api:8111', 'http://second-api:8111']) {
      vi.stubEnv('BACKEND_ORIGIN', origin);
      const response = proxy(request);
      expect(response.headers.get('x-middleware-rewrite')).toBe(
        `${origin}/api/inspections?source=a%2Fb`,
      );
      expect(response.headers.get('location')).toBeNull();
      expect(request.bodyUsed).toBe(false);
    }
    expect(await request.text()).toContain('public_url');
  });

  it.each(['/api', '/api/providers', '/health', '/health/ready'])(
    'forwards backend path %s',
    (path) => {
      vi.stubEnv('BACKEND_ORIGIN', 'http://candidate-api:8111');
      expect(
        proxy(new NextRequest(`http://localhost:8137${path}`)).headers.get(
          'x-middleware-rewrite',
        ),
      ).toBe(`http://candidate-api:8111${path}`);
    },
  );

  it.each(['/api-docs/', '/healthy/', '/storage-upload/'])(
    'keeps frontend path %s local',
    (path) => {
      expect(
        proxy(new NextRequest(`http://localhost:8137${path}`)).headers.get(
          'x-middleware-rewrite',
        ),
      ).toBeNull();
    },
  );

  it.each([
    'invalid',
    'file:///tmp/api',
    'http://user:secret@api:8111',
    'http://api:8111/base',
  ])('fails closed for an invalid backend origin', async (origin) => {
    vi.stubEnv('BACKEND_ORIGIN', origin);
    const response = proxy(
      new NextRequest('http://localhost:8137/api/providers'),
    );
    expect(response.status).toBe(503);
    expect(response.headers.get('x-middleware-rewrite')).toBeNull();
    expect(await response.text()).not.toContain(origin);
  });
});
