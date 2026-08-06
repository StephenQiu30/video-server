import axios, { type AxiosRequestConfig } from 'axios';

type ProblemDetails = {
  code: string;
  title: string;
  detail: string;
};

export type RequestOptions = AxiosRequestConfig;

const apiClient = axios.create({
  adapter: 'fetch',
  baseURL: globalThis.location.origin,
  headers: { Accept: 'application/json' },
});

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    readonly title: string,
    readonly detail: string,
  ) {
    super(detail);
    this.name = 'ApiError';
  }
}

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  try {
    const response = await apiClient.request<T>({
      ...options,
      url: path,
    });
    return response.data;
  } catch (error) {
    if (axios.isCancel(error)) {
      throw error;
    }
    throw toApiError(error);
  }
}

export function createIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

export function displayError(error: unknown): string {
  return error instanceof ApiError
    ? error.detail
    : '发生未知错误，请稍后重试。';
}

function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status ?? 0;
    const problem = parseProblemDetails(error.response?.data);
    if (problem) {
      return new ApiError(status, problem.code, problem.title, problem.detail);
    }
    return new ApiError(
      status,
      'request_failed',
      '请求失败',
      '服务暂时不可用，请稍后重试。',
    );
  }
  return new ApiError(
    0,
    'request_failed',
    '请求失败',
    '服务暂时不可用，请稍后重试。',
  );
}

function parseProblemDetails(value: unknown): ProblemDetails | null {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const problem = value as Partial<ProblemDetails>;
  return problem.code && problem.title && problem.detail
    ? (problem as ProblemDetails)
    : null;
}
