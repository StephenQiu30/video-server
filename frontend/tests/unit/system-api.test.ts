import { request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import {
  liveHealthLiveGet,
  readyHealthReadyGet,
} from '@/services/video/system';

const requestMock = vi.mocked(request);

describe('system API', () => {
  it('uses same-origin liveness and readiness endpoints', async () => {
    requestMock
      .mockResolvedValueOnce({ status: 'ok' })
      .mockResolvedValueOnce({ status: 'ok', service: 'api' });

    await expect(liveHealthLiveGet()).resolves.toEqual({ status: 'ok' });
    await expect(readyHealthReadyGet()).resolves.toEqual({
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
