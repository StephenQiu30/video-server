import { AxiosError, type AxiosRequestConfig } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { httpClient, request } from '@/utils/request';

const originalAdapter = httpClient.defaults.adapter;

describe('silent JWT refresh', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    httpClient.defaults.adapter = originalAdapter;
  });

  it('refreshes once and retries the original request after a 401', async () => {
    let protectedAttempts = 0;
    const adapter = vi.fn(async (config: AxiosRequestConfig) => {
      if (config.url === '/api/auth/refresh') {
        return response(config, { email: 'user@example.com' });
      }
      protectedAttempts += 1;
      if (protectedAttempts === 1) {
        throw new AxiosError(
          'Unauthorized',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          response(config, { code: 'unauthenticated' }, 401),
        );
      }
      return response(config, { status: 'restored' });
    });
    httpClient.defaults.adapter = adapter;

    await expect(request('/api/downloads/history')).resolves.toEqual({
      status: 'restored',
    });
    expect(adapter.mock.calls.map(([config]) => config.url)).toEqual([
      '/api/downloads/history',
      '/api/auth/refresh',
      '/api/downloads/history',
    ]);
  });
});

function response(config: AxiosRequestConfig, data: unknown, status = 200) {
  return {
    config,
    data,
    headers: {},
    status,
    statusText: status === 200 ? 'OK' : 'Unauthorized',
  };
}
