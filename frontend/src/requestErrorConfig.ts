import type { RequestConfig } from '@umijs/max';

type ProblemDetails = {
  code: string;
  detail: string;
  title: string;
};

type ResponseError = {
  response?: {
    data?: unknown;
    status?: number;
  };
};

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

export const requestErrorConfig: RequestConfig = {
  errorConfig: {
    errorHandler(error: unknown) {
      throw toApiError(error);
    },
  },
  timeout: 30000,
};

export function displayError(error: unknown): string {
  return error instanceof ApiError
    ? error.detail
    : '发生未知错误，请稍后重试。';
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }
  const responseError = error as ResponseError;
  const status = responseError.response?.status ?? 0;
  const problem = parseProblemDetails(responseError.response?.data);
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

function parseProblemDetails(value: unknown): ProblemDetails | null {
  if (!value || typeof value !== 'object') {
    return null;
  }
  const problem = value as Partial<ProblemDetails>;
  return problem.code && problem.title && problem.detail
    ? (problem as ProblemDetails)
    : null;
}
