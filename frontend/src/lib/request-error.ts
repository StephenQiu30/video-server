import {
  localizedErrorMessage,
  statusErrorMessage,
} from '@/lib/error-messages';

type ProblemDetails = {
  code: string;
  detail: string;
  title: string;
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

export function displayError(error: unknown): string {
  if (!(error instanceof ApiError)) return '发生未知错误，请稍后重试。';
  return (
    localizedErrorMessage(error.code) ??
    (containsChinese(error.detail)
      ? error.detail
      : statusErrorMessage(error.status))
  );
}

export function apiErrorFrom(
  status: number,
  payload: unknown,
  fallbackDetail?: string,
): ApiError {
  const problem = parseProblemDetails(payload);
  if (problem) {
    return new ApiError(status, problem.code, problem.title, problem.detail);
  }
  return new ApiError(
    status,
    'request_failed',
    '请求失败',
    fallbackDetail ??
      (status >= 500
        ? '服务暂时不可用，请稍后重试。'
        : '请求未能完成，请检查后重试。'),
  );
}

function parseProblemDetails(value: unknown): ProblemDetails | null {
  if (!value || typeof value !== 'object') return null;
  const problem = value as Partial<ProblemDetails>;
  return problem.code && problem.title && problem.detail
    ? (problem as ProblemDetails)
    : null;
}

function containsChinese(value: string): boolean {
  return /[\u3400-\u9fff]/u.test(value);
}
