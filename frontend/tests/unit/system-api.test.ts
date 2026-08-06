import { afterEach, describe, expect, it, vi } from 'vitest';

import { getSystemReady } from '@/shared/api/system';

afterEach(() => vi.unstubAllGlobals());

describe('getSystemReady', () => {
  it('uses the same-origin health endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', service: 'api' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(getSystemReady()).resolves.toEqual({
      status: 'ok',
      service: 'api',
    });
    expect(fetchMock).toHaveBeenCalledWith('/health/ready', {
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    });
  });

  it('rejects an unavailable server', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('', { status: 503 })),
    );

    await expect(getSystemReady()).rejects.toThrow('server_not_ready');
  });
});
