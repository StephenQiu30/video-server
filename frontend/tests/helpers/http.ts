import { vi } from 'vitest';

import { httpClient } from '@/utils/request';

export function mockHttpResponses(...values: unknown[]): void {
  for (const value of values) {
    vi.mocked(httpClient.request).mockResolvedValueOnce({
      data: value,
    } as never);
  }
}

export function mockHttpError(error: Error): void {
  vi.mocked(httpClient.request).mockRejectedValueOnce(error);
}

export function httpRequests() {
  return vi.mocked(httpClient.request).mock.calls.map(([config]) => config);
}
