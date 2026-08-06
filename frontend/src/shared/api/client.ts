const API_ROOT = '/api/v1';

type ProblemDetails = {
  code: string;
  title: string;
  detail: string;
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

export async function apiRequest<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  return response.json() as Promise<T>;
}

export function jsonPost(body?: object, idempotencyKey?: string): RequestInit {
  return {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
    headers: idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined,
  };
}

export function createIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

export function displayError(error: unknown): string {
  return error instanceof ApiError
    ? error.detail
    : '发生未知错误，请稍后重试。';
}

async function responseError(response: Response): Promise<ApiError> {
  try {
    const value = (await response.json()) as Partial<ProblemDetails>;
    if (value.code && value.title && value.detail) {
      return new ApiError(
        response.status,
        value.code,
        value.title,
        value.detail,
      );
    }
  } catch {
    // The stable fallback below intentionally hides upstream response bodies.
  }
  return new ApiError(
    response.status,
    'request_failed',
    '请求失败',
    '服务暂时不可用，请稍后重试。',
  );
}
