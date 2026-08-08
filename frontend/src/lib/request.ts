import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';

import { apiErrorFrom } from '@/requestErrorConfig';

const API_TIMEOUT_MS = 30_000;

export type RequestOptions = AxiosRequestConfig & {
  getResponse?: boolean;
  skipErrorHandler?: boolean;
};

export const httpClient: AxiosInstance = axios.create({
  timeout: API_TIMEOUT_MS,
  withCredentials: true,
  headers: { Accept: 'application/json' },
});

httpClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (!axios.isAxiosError(error)) {
      return Promise.reject(error);
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
  const response = await httpClient.request<T>({
    url,
    ...config,
  });
  return response.data;
}
