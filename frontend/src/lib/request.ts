import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from 'axios';

import { getCurrentUser, refreshUserSession } from '@/api/auth';
import { ApiError, apiErrorFrom } from '@/lib/request-error';

const API_TIMEOUT_MS = 30_000;

export type RequestOptions = AxiosRequestConfig & {
  getResponse?: boolean;
  skipAuthRedirect?: boolean;
  skipAuthRefresh?: boolean;
  skipErrorHandler?: boolean;
};

type RetriableRequestConfig = AxiosRequestConfig & {
  authRetried?: boolean;
  skipAuthRedirect?: boolean;
  skipAuthRefresh?: boolean;
};

let refreshRequest: Promise<void> | null = null;

export const httpClient: AxiosInstance = axios.create({
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    'X-Client-Platform': 'web',
  },
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) return Promise.reject(error);

    const config = error.config as RetriableRequestConfig | undefined;
    if (shouldRefresh(error, config)) {
      config.authRetried = true;
      try {
        await refreshAccessToken();
        return await httpClient.request(config);
      } catch (refreshError) {
        if (!config.skipAuthRedirect) redirectToLogin();
        return Promise.reject(refreshError);
      }
    }

    if (!error.response) {
      return Promise.reject(
        apiErrorFrom(0, null, '网络连接失败，请检查网络后重试。'),
      );
    }
    return Promise.reject(
      apiErrorFrom(error.response.status, error.response.data),
    );
  },
);

function shouldRefresh(
  error: AxiosError,
  config: RetriableRequestConfig | undefined,
): config is RetriableRequestConfig {
  if (
    error.response?.status !== 401 ||
    !config ||
    config.authRetried ||
    config.skipAuthRefresh
  )
    return false;
  return ![
    '/api/auth/login',
    '/api/auth/register',
    '/api/auth/registration-code',
    '/api/auth/refresh',
  ].includes(config.url ?? '');
}

async function refreshAccessToken(): Promise<void> {
  if (!refreshRequest) {
    refreshRequest = withBrowserRefreshLock(async (recheckSession) => {
      if (recheckSession && (await hasCurrentSession())) return;
      try {
        await refreshUserSession({
          skipAuthRefresh: true,
          skipAuthRedirect: true,
        });
      } catch (error) {
        if (error instanceof ApiError && error.code === 'refresh_in_progress') {
          return;
        }
        throw error;
      }
    }).finally(() => {
      refreshRequest = null;
    });
  }
  await refreshRequest;
}

async function withBrowserRefreshLock(
  action: (recheckSession: boolean) => Promise<void>,
): Promise<void> {
  if (typeof navigator === 'undefined' || !navigator.locks) {
    return action(false);
  }
  return navigator.locks.request('framefetch-auth-refresh', () => action(true));
}

async function hasCurrentSession(): Promise<boolean> {
  try {
    await getCurrentUser({ skipAuthRefresh: true, skipAuthRedirect: true });
    return true;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return false;
    throw error;
  }
}

function redirectToLogin(): void {
  if (
    typeof window === 'undefined' ||
    window.location.pathname.startsWith('/user/')
  ) {
    return;
  }
  const redirect = `${window.location.pathname}${window.location.search}`;
  window.location.replace(
    `/user/login?redirect=${encodeURIComponent(redirect)}`,
  );
}

export async function request<T>(
  url: string,
  options: RequestOptions = {},
): Promise<T> {
  if (!url.startsWith('/') || url.startsWith('//')) {
    throw new TypeError('Only same-origin API paths are allowed.');
  }
  const {
    getResponse: _getResponse,
    skipErrorHandler: _skip,
    ...config
  } = options;
  const response = await httpClient.request<T>({ url, ...config });
  return response.data;
}
