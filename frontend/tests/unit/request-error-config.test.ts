import { describe, expect, it } from 'vitest';

import { ApiError, apiErrorFrom, displayError } from '@/utils/requestErrorConfig';

describe('request errors', () => {
  it('converts RFC problem responses into ApiError', () => {
    const error = apiErrorFrom(409, {
      code: 'idempotency_conflict',
      title: '请求冲突',
      detail: '同一请求键不能用于不同负载。',
    });

    expect(error).toMatchObject({
      code: 'idempotency_conflict',
      detail: '同一请求键不能用于不同负载。',
      status: 409,
      title: '请求冲突',
    });
  });

  it('uses safe fallback messages for unknown failures', () => {
    const error = apiErrorFrom(502, { title: 'Incomplete' });
    expect(error.detail).toBe('服务暂时不可用，请稍后重试。');
    expect(displayError(new Error('secret upstream detail'))).toBe(
      '发生未知错误，请稍后重试。',
    );
    expect(displayError(apiError(0, 'x', 'x', '安全信息'))).toBe('安全信息');
  });
});

function apiError(
  status: number,
  code: string,
  title: string,
  detail: string,
) {
  return new ApiError(status, code, title, detail);
}