import { request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import { getLiveness, getReadiness } from '@/services/video/system';

const requestMock = vi.mocked(request);

describe('system API', () => {
  it('uses same-origin liveness and readiness endpoints', async () => {
    requestMock
      .mockResolvedValueOnce({ status: 'ok' })
      .mockResolvedValueOnce({ status: 'ok', service: 'api' });

    await expect(getLiveness()).resolves.toEqual({ status: 'ok' });
    await expect(getReadiness()).resolves.toEqual({
      status: 'ok',
      service: 'api',
    });

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      '/health/live',
      expect.objectContaining({ method: 'GET' }),
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/health/ready',
      expect.objectContaining({ method: 'GET' }),
    );
  });
});
