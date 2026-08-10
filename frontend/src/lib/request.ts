import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
} from 'axios';

import { apiErrorFrom } from '@/lib/request-error';

const API_TIMEOUT_MS = 30_000;

export type RequestOptions = AxiosRequestConfig & {
  getResponse?: boolean;
  skipErrorHandler?: boolean;
};

type RetriableRequestConfig = AxiosRequestConfig & { authRetried?: boolean };

let refreshRequest: Promise<void> | null = null;

export const httpClient: AxiosInstance = axios.create({
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: { Accept: 'application/json' },
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
        redirectToLogin();
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
  if (error.response?.status !== 401 || !config || config.authRetried)
    return false;
  return ![
    '/api/auth/login',
    '/api/auth/register',
    '/api/auth/refresh',
  ].includes(config.url ?? '');
}

async function refreshAccessToken(): Promise<void> {
  if (!refreshRequest) {
    refreshRequest = httpClient
      .post('/api/auth/refresh')
      .then(() => undefined)
      .finally(() => {
        refreshRequest = null;
      });
  }
  await refreshRequest;
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
