import {
  AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { httpClient, request } from '@/lib/request';

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
    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => {
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

  it('shares one refresh request across concurrent protected failures', async () => {
    const attempts = new Map<string, number>();
    let refreshCalls = 0;
    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => {
      if (config.url === '/api/auth/refresh') {
        refreshCalls += 1;
        return response(config, { email: 'user@example.com' });
      }

      const attempt = (attempts.get(config.url ?? '') ?? 0) + 1;
      attempts.set(config.url ?? '', attempt);
      if (attempt === 1) {
        throw new AxiosError(
          'Unauthorized',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          response(
            config,
            {
              code: 'unauthenticated',
              detail: '登录状态已失效',
              title: '需要登录',
            },
            401,
          ),
        );
      }
      return response(config, { path: config.url, status: 'restored' });
    });
    httpClient.defaults.adapter = adapter;

    await expect(
      Promise.all([
        request('/api/downloads/history'),
        request('/api/users/me'),
      ]),
    ).resolves.toEqual([
      { path: '/api/downloads/history', status: 'restored' },
      { path: '/api/users/me', status: 'restored' },
    ]);
    expect(refreshCalls).toBe(1);
    expect(attempts).toEqual(
      new Map([
        ['/api/downloads/history', 2],
        ['/api/users/me', 2],
      ]),
    );
  });

  it('does not refresh authentication endpoints and keeps safe problem details', async () => {
    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => {
      throw new AxiosError(
        'Unauthorized',
        'ERR_BAD_REQUEST',
        config,
        undefined,
        response(
          config,
          {
            code: 'invalid_credentials',
            detail: '邮箱或密码错误',
            title: '登录失败',
          },
          401,
        ),
      );
    });
    httpClient.defaults.adapter = adapter;

    await expect(
      request('/api/auth/login', {
        data: { email: 'user@example.com', password: 'invalid' },
        method: 'POST',
      }),
    ).rejects.toMatchObject({
      code: 'invalid_credentials',
      detail: '邮箱或密码错误',
      status: 401,
      title: '登录失败',
    });
    expect(adapter).toHaveBeenCalledOnce();
    expect(adapter.mock.calls[0]?.[0].url).toBe('/api/auth/login');
  });
});

function response(
  config: InternalAxiosRequestConfig,
  data: unknown,
  status = 200,
): AxiosResponse {
  return {
    config,
    data,
    headers: {},
    status,
    statusText: status === 200 ? 'OK' : 'Unauthorized',
  };
}
