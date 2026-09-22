import {
  AxiosError,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { httpClient, request } from '@/lib/request';
import {
  advanceSessionGeneration,
  onSessionExpired,
} from '@/lib/session-events';

const originalAdapter = httpClient.defaults.adapter;

describe('silent JWT refresh', () => {
  const originalLocks = Object.getOwnPropertyDescriptor(navigator, 'locks');

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    httpClient.defaults.adapter = originalAdapter;
    if (originalLocks) {
      Object.defineProperty(navigator, 'locks', originalLocks);
    } else {
      Reflect.deleteProperty(navigator, 'locks');
    }
    vi.unstubAllGlobals();
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
              message: '登录状态已失效',
              data: null,
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

  it('rechecks the session after another browser tab holds the refresh lock', async () => {
    let attempts = 0;
    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => {
      attempts += 1;
      if (attempts === 1) {
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
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      value: {
        request: vi.fn(async (_name: string, callback: () => Promise<void>) =>
          callback(),
        ),
      },
    });

    await expect(request('/api/downloads/history')).resolves.toEqual({
      status: 'restored',
    });
    expect(adapter.mock.calls.map(([config]) => config.url)).toEqual([
      '/api/downloads/history',
      '/api/auth/me',
      '/api/downloads/history',
    ]);
  });

  it('retries without redirecting when a concurrent refresh is reported', async () => {
    let protectedAttempts = 0;
    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => {
      if (config.url === '/api/auth/refresh') {
        throw new AxiosError(
          'Conflict',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          response(
            config,
            {
              code: 'refresh_in_progress',
              message: 'Another request refreshed this session.',
              data: null,
            },
            409,
          ),
        );
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
            message: '邮箱或密码错误',
            data: null,
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
      title: '邮箱或密码错误',
    });
    expect(adapter).toHaveBeenCalledOnce();
    expect(adapter.mock.calls[0]?.[0].url).toBe('/api/auth/login');
  });

  it.each([0, 403, 429, 503])(
    'keeps identity when refresh fails with %s',
    async (status) => {
      const expired = vi.fn();
      const unsubscribe = onSessionExpired(expired);
      httpClient.defaults.adapter = async (config) => {
        const resultStatus = config.url === '/api/auth/refresh' ? status : 401;
        throw new AxiosError(
          'failed',
          'ERR_BAD_REQUEST',
          config,
          undefined,
          resultStatus
            ? response(
                config,
                { code: 'request_failed', message: '失败', data: null },
                resultStatus,
              )
            : undefined,
        );
      };
      try {
        await expect(request('/api/downloads/history')).rejects.toMatchObject({
          status,
        });
        expect(expired).not.toHaveBeenCalled();
      } finally {
        unsubscribe();
      }
    },
  );

  it('reports confirmed session expiry to the identity owner', async () => {
    const expired = vi.fn();
    const unsubscribe = onSessionExpired(expired);
    httpClient.defaults.adapter = async (config) => {
      throw new AxiosError(
        'expired',
        '',
        config,
        undefined,
        response(
          config,
          { code: 'unauthenticated', message: '失效', data: null },
          401,
        ),
      );
    };
    try {
      await expect(request('/api/downloads/history')).rejects.toMatchObject({
        status: 401,
      });
      expect(expired).toHaveBeenCalledOnce();
    } finally {
      unsubscribe();
    }
  });

  it('keeps identity when replayed business authorization is denied', async () => {
    const expired = vi.fn();
    const unsubscribe = onSessionExpired(expired);
    let attempts = 0;
    httpClient.defaults.adapter = async (config) => {
      if (config.url === '/api/auth/refresh') return response(config, {});
      throw new AxiosError(
        'denied',
        '',
        config,
        undefined,
        response(
          config,
          { code: 'forbidden', message: '拒绝', data: null },
          ++attempts === 1 ? 401 : 403,
        ),
      );
    };
    try {
      await expect(request('/api/admin/users')).rejects.toMatchObject({
        status: 403,
      });
      expect(expired).not.toHaveBeenCalled();
    } finally {
      unsubscribe();
    }
  });

  it('does not treat a refresh conflict as a successful session recovery', async () => {
    const expired = vi.fn();
    const unsubscribe = onSessionExpired(expired);
    const paths: string[] = [];
    httpClient.defaults.adapter = async (config) => {
      paths.push(config.url ?? '');
      const refresh = config.url === '/api/auth/refresh';
      throw new AxiosError(
        'failed',
        '',
        config,
        undefined,
        response(
          config,
          {
            code: refresh ? 'refresh_in_progress' : 'unauthenticated',
            message: '等待刷新',
            data: null,
          },
          refresh ? 409 : 401,
        ),
      );
    };
    try {
      await expect(request('/api/downloads/history')).rejects.toMatchObject({
        status: 409,
      });
      expect(paths).toEqual([
        '/api/downloads/history',
        '/api/auth/refresh',
        '/api/auth/me',
      ]);
      expect(expired).not.toHaveBeenCalled();
    } finally {
      unsubscribe();
    }
  });

  it('discards a stale identity response without refreshing or replaying it', async () => {
    const expired = vi.fn();
    const unsubscribe = onSessionExpired(expired);
    httpClient.defaults.adapter = async (config) => {
      advanceSessionGeneration();
      throw new AxiosError(
        'expired',
        '',
        config,
        undefined,
        response(config, {}, 401),
      );
    };
    try {
      await expect(request('/api/downloads/history')).rejects.toMatchObject({
        code: 'ERR_CANCELED',
      });
      expect(expired).not.toHaveBeenCalled();
    } finally {
      unsubscribe();
    }
  });
});

function response(
  config: InternalAxiosRequestConfig,
  data: unknown,
  status = 200,
): AxiosResponse {
  return {
    config,
    data: status === 200 ? { code: 'ok', message: 'OK', data } : data,
    headers: {},
    status,
    statusText: status === 200 ? 'OK' : 'Unauthorized',
  };
}
