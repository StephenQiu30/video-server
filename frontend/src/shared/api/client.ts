type ProblemDetails = {
  code: string;
  title: string;
  detail: string;
};

type RequestParameter =
  | string
  | number
  | boolean
  | null
  | undefined
  | RequestParameter[];

export type RequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  params?: Record<string, RequestParameter>;
  data?: unknown;
  credentials?: RequestCredentials;
  signal?: AbortSignal;
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

export async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { data, params, ...init } = options;
  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...options.headers,
  };
  if (data !== undefined && !(data instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(withQuery(path, params), {
    ...init,
    body:
      data === undefined
        ? undefined
        : data instanceof FormData
          ? data
          : JSON.stringify(data),
    credentials: options.credentials ?? 'same-origin',
    headers,
  });
  if (!response.ok) {
    throw await responseError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
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

function withQuery(
  path: string,
  params: Record<string, RequestParameter> | undefined,
): string {
  if (!params) {
    return path;
  }
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item !== undefined && item !== null) {
        query.append(key, String(item));
      }
    }
  }
  const suffix = query.toString();
  return suffix ? `${path}${path.includes('?') ? '&' : '?'}${suffix}` : path;
}
