import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from 'axios';

import { getCurrentUser, refreshUserSession } from '@/api/auth';
import { ApiError, apiErrorFrom } from '@/lib/request-error';
import { reportSessionExpired, sessionGeneration } from '@/lib/session-events';

const API_TIMEOUT_MS = 30_000;

export type RequestOptions = AxiosRequestConfig & {
  getResponse?: boolean;
  skipAuthRefresh?: boolean;
  skipErrorHandler?: boolean;
};

type RetriableRequestConfig = AxiosRequestConfig & {
  authRetried?: boolean;
  sessionGeneration?: number;
  skipAuthRefresh?: boolean;
};

let refreshRequest: Promise<void> | null = null;
let refreshGeneration = -1;

export const httpClient: AxiosInstance = axios.create({
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
    'X-Client-Platform': 'web',
  },
});

httpClient.interceptors.request.use((config) => {
  const sessionConfig = config as RetriableRequestConfig;
  sessionConfig.sessionGeneration ??= sessionGeneration();
  return config;
});

httpClient.interceptors.response.use(
  (response) => {
    assertCurrentSession(response.config as RetriableRequestConfig);
    return response;
  },
  async (error: unknown) => {
    if (axios.isCancel(error) || !axios.isAxiosError(error))
      return Promise.reject(error);

    const config = error.config as RetriableRequestConfig | undefined;
    if (config) assertCurrentSession(config);
    if (config && shouldRefresh(error, config)) {
      config.authRetried = true;
      try {
        await refreshAccessToken();
      } catch (refreshError) {
        if (refreshError instanceof ApiError && refreshError.status === 401) {
          reportSessionExpired(config.sessionGeneration ?? sessionGeneration());
        }
        return Promise.reject(refreshError);
      }
      // A replayed business failure is not a failed session refresh.
      assertCurrentSession(config);
      return httpClient.request(config);
    }

    if (config?.authRetried && error.response?.status === 401) {
      reportSessionExpired(config.sessionGeneration ?? sessionGeneration());
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

function assertCurrentSession(config: RetriableRequestConfig): void {
  if (
    config.sessionGeneration !== undefined &&
    config.sessionGeneration !== sessionGeneration()
  ) {
    throw new axios.CanceledError('Session changed');
  }
}

function shouldRefresh(
  error: AxiosError,
  config: RetriableRequestConfig | undefined,
): boolean {
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
  const current = sessionGeneration();
  if (!refreshRequest || refreshGeneration !== current) {
    refreshGeneration = current;
    const pending = withBrowserRefreshLock(async (recheckSession) => {
      if (current !== sessionGeneration())
        throw new axios.CanceledError('Session changed');
      if (recheckSession && (await hasCurrentSession())) return;
      try {
        await refreshUserSession({
          skipAuthRefresh: true,
        });
      } catch (error) {
        if (error instanceof ApiError && error.code === 'refresh_in_progress') {
          if (await hasCurrentSession()) return;
        }
        throw error;
      }
    }).finally(() => {
      if (refreshRequest === pending) refreshRequest = null;
    });
    refreshRequest = pending;
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
    await getCurrentUser({ skipAuthRefresh: true });
    return true;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return false;
    throw error;
  }
}

type ResponseData<T> = T extends {
  code: string;
  message: string;
  data: infer D;
}
  ? D
  : T;

export async function request<T>(
  url: string,
  options: RequestOptions = {},
): Promise<ResponseData<T>> {
  if (!url.startsWith('/') || url.startsWith('//')) {
    throw new TypeError('Only same-origin API paths are allowed.');
  }
  const {
    getResponse: _getResponse,
    skipErrorHandler: _skip,
    ...config
  } = options;
  const response = await httpClient.request<T>({ url, ...config });
  const payload = response.data;
  if (
    payload &&
    typeof payload === 'object' &&
    'code' in payload &&
    'message' in payload &&
    'data' in payload
  ) {
    return payload.data as ResponseData<T>;
  }
  return payload as ResponseData<T>;
}
