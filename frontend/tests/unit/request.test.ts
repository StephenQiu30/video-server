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

  it('unwraps the generated JSON contract, including nullable data', async () => {
    vi.mocked(httpClient.request).mockResolvedValueOnce({
      data: { code: 'ok', message: 'OK', data: { id: 'job' } },
    } as never);
    await expect(request('/api/downloads/job')).resolves.toEqual({ id: 'job' });
    vi.mocked(httpClient.request).mockResolvedValueOnce({
      data: { code: 'ok', message: 'OK', data: null },
    } as never);
    await expect(request('/api/downloads/job/analysis')).resolves.toBeNull();
  });

  it('keeps binary content and no-content responses intact', async () => {
    const blob = new Blob(['file']);
    vi.mocked(httpClient.request).mockResolvedValueOnce({
      data: blob,
    } as never);
    await expect(
      request('/api/files/file', { responseType: 'blob' }),
    ).resolves.toBe(blob);
    vi.mocked(httpClient.request).mockResolvedValueOnce({
      data: undefined,
    } as never);
    await expect(
      request('/api/auth/logout', { method: 'POST' }),
    ).resolves.toBeUndefined();
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
