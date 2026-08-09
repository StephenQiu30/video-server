import { describe, expect, it, vi } from 'vitest';

import { httpClient, request } from '@/lib/request';

describe('Axios request wrapper', () => {
  it('unwraps response data and keeps generated request options', async () => {
    const payload = { status: 'ok' };
    vi.mocked(httpClient.request).mockResolvedValueOnce({
      data: payload,
    } as never);

    await expect(
      request('/health/live', { method: 'GET', params: { verbose: false } }),
    ).resolves.toEqual(payload);
    expect(httpClient.request).toHaveBeenCalledWith({
      method: 'GET',
      params: { verbose: false },
      url: '/health/live',
    });
  });

  it('rejects absolute cross-origin request targets', async () => {
    await expect(request('https://example.com/private')).rejects.toThrow(
      'Only same-origin API paths are allowed.',
    );
    await expect(request('//example.com/private')).rejects.toThrow(
      'Only same-origin API paths are allowed.',
    );
    expect(httpClient.request).not.toHaveBeenCalled();
  });
});
