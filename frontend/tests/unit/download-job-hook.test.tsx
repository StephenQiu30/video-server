import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useDownloadJob } from '@/hooks/useDownloadJob';
import { job } from '../fixtures/download-fixtures';

const runtime = vi.hoisted(() => ({
  getDownload: vi.fn(),
}));

vi.mock('@/services/download', () => ({
  cancelDownload: vi.fn(),
  createIdempotencyKey: () => 'test-key',
  displayError: (reason: unknown) =>
    reason instanceof Error ? reason.message : '请求失败',
  getDownload: runtime.getDownload,
  issueDownloadUrl: vi.fn(),
  retryDownload: vi.fn(),
  triggerBrowserDownload: vi.fn(),
}));

describe('useDownloadJob', () => {
  beforeEach(() => {
    runtime.getDownload.mockReset();
  });

  it('never exposes the previous job after the requested id changes', async () => {
    const first = { ...job('succeeded'), id: 'first-job' };
    let rejectSecond: ((reason: Error) => void) | undefined;
    runtime.getDownload.mockResolvedValueOnce(first).mockImplementationOnce(
      () =>
        new Promise((_, reject) => {
          rejectSecond = reject;
        }),
    );
    const { result, rerender } = renderHook(
      ({ jobId }: { jobId: string }) => useDownloadJob(jobId, 60_000),
      { initialProps: { jobId: 'first-job' } },
    );

    await waitFor(() => expect(result.current.job?.id).toBe('first-job'));
    rerender({ jobId: 'second-job' });
    expect(result.current.job).toBeNull();
    expect(result.current.loading).toBe(true);

    act(() => rejectSecond?.(new Error('second job unavailable')));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.job).toBeNull();
    expect(result.current.error).toBe('second job unavailable');
  });
});
