import { describe, expect, it } from 'vitest';

import {
  ApiError,
  displayError,
  requestErrorConfig,
} from '@/requestErrorConfig';

describe('requestErrorConfig', () => {
  it('converts code, title, and detail problem responses into ApiError', () => {
    const problem = {
      code: 'idempotency_conflict',
      title: '请求冲突',
      detail: '同一请求键不能用于不同负载。',
    };

    expect(
      handledError({ response: { data: problem, status: 409 } }),
    ).toMatchObject({
      code: problem.code,
      detail: problem.detail,
      status: 409,
      title: problem.title,
    });
  });

  it('uses a stable fallback for incomplete and unknown failures', () => {
    expect(
      handledError({
        response: { data: { title: 'Incomplete' }, status: 502 },
      }),
    ).toMatchObject({
      code: 'request_failed',
      detail: '服务暂时不可用，请稍后重试。',
      status: 502,
      title: '请求失败',
    });
    expect(displayError(new Error('secret upstream detail'))).toBe(
      '发生未知错误，请稍后重试。',
    );
    expect(displayError(new ApiError(0, 'x', 'x', '安全信息'))).toBe(
      '安全信息',
    );
  });
});

function handledError(error: unknown): unknown {
  const errorHandler = requestErrorConfig.errorConfig?.errorHandler;
  if (!errorHandler) {
    throw new Error('request error handler is required');
  }
  try {
    errorHandler(error as never, {} as never);
  } catch (reason) {
    return reason;
  }
  throw new Error('request error handler must throw');
}
