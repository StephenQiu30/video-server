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
  return localizedErrorDetails[error.code] ?? error.detail;
}

const localizedErrorDetails: Record<string, string> = {
  download_not_ready: '文件仍在处理中，请等待任务完成后再下载。',
  format_unavailable: '原下载规格目前不可用，请重新解析视频并选择其他格式。',
  invalid_request: '提交内容不符合要求，请检查各字段后重试。',
  invalid_state: '当前任务状态不支持此操作，请刷新页面后重试。',
  not_found: '任务或相关资源不存在，请返回下载记录确认。',
  provider_link_unavailable: '原视频链接已经失效，请复制新的公开分享链接。',
  resource_expired: '文件已超过保留期限，请使用“重新下载”生成新文件。',
};

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
