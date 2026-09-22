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

  it('overwrites caller forwarded host before the trusted API hop', () => {
    const response = proxy(
      new NextRequest('http://localhost:8101/api/auth/login', {
        method: 'POST',
        headers: { host: 'localhost:8101', 'x-forwarded-host': 'evil.example' },
      }),
    );
    expect(response.headers.get('x-middleware-request-x-forwarded-host')).toBe(
      'localhost:8101',
    );
    expect(response.headers.get('x-middleware-request-x-forwarded-proto')).toBe(
      'http',
    );
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

  it.each(['/api/auth/me/', '/api/inspections/', '/health/ready/'])(
    'normalizes %s without redirecting the browser to the internal host',
    (path) => {
      vi.stubEnv('BACKEND_ORIGIN', 'http://api:8111');
      const response = proxy(
        new NextRequest(`http://localhost:8101${path}?test=1`, {
          method: 'POST',
          body: '{}',
        }),
      );
      expect(response.headers.get('x-middleware-rewrite')).toBe(
        `http://api:8111${path.slice(0, -1)}?test=1`,
      );
      expect(response.headers.get('location')).toBeNull();
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
    expect(await response.clone().json()).toEqual({
      code: 'service_unavailable',
      message: 'API routing is unavailable.',
      data: null,
    });
    expect(response.headers.get('x-middleware-rewrite')).toBeNull();
    expect(await response.text()).not.toContain(origin);
  });
});
