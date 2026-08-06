export type ProblemDetails = {
  status: number | null;
  code: string | null;
  title: string;
  detail: string;
};

function objectValue(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === 'number' && Number.isInteger(value) ? value : null;
}

/** Convert Umi request errors and Problem Details without exposing raw payloads. */
export function toProblem(error: unknown): ProblemDetails {
  const root = objectValue(error);
  const response = root && objectValue(root.response);
  const payload =
    (response && objectValue(response.data)) ||
    (root && objectValue(root.data)) ||
    root;
  const status =
    numberValue(payload?.status) ??
    numberValue(response?.status) ??
    numberValue(root?.status);
  const code = stringValue(payload?.code);
  const detail = stringValue(payload?.detail);
  const title = stringValue(payload?.title);
  return {
    status,
    code,
    title: title ?? '请求失败',
    detail:
      detail ??
      (status && status >= 500
        ? '服务暂不可用，请稍后重试'
        : '请求未完成，请检查后重试'),
  };
}

export function isTransient(error: unknown): boolean {
  const problem = toProblem(error);
  return (
    problem.status === null ||
    problem.status >= 500 ||
    problem.status === 408 ||
    problem.status === 429
  );
}

export function isNotFoundOrExpired(error: unknown): boolean {
  const status = toProblem(error).status;
  return status === 403 || status === 404 || status === 410 || status === 422;
}
