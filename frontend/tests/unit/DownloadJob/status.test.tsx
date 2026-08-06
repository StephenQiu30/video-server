import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  isActiveJob,
  openDownloadUrl,
  useDownloadJob,
  useDownloadUrl,
} from '@/pages/DownloadJob/hooks';
import { videoApi } from '@/utils/videoApi';

const job = {
  id: 'job-1',
  status: 'queued',
  stage: null,
  progress_percent: null,
  downloaded_bytes: null,
  total_bytes: null,
  error: null,
  artifact: null,
};

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('DownloadJob polling and file navigation', () => {
  beforeEach(() => vi.restoreAllMocks());

  it('polls only active jobs at the two-second interval', async () => {
    const getDownload = vi
      .spyOn(videoApi, 'getDownload')
      .mockResolvedValue(job);
    const { result } = renderHook(() => useDownloadJob('job-1'), { wrapper });
    await waitFor(() => expect(result.current.data?.status).toBe('queued'));
    expect(getDownload).toHaveBeenCalledTimes(1);
  });

  it('navigates to a signed URL only when explicitly requested', () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    openDownloadUrl('https://minio.example.test/signed/path');
    expect(click).toHaveBeenCalledTimes(1);
    expect(document.body.querySelector('a')).toBeNull();
  });

  it('classifies terminal jobs and configures bounded retries', () => {
    expect(isActiveJob(null)).toBe(false);
    expect(isActiveJob({ ...job, status: 'running' } as never)).toBe(true);
    expect(isActiveJob({ ...job, status: 'succeeded' } as never)).toBe(false);
  });

  it('requests temporary URLs only with a job ID and rejects malformed responses', async () => {
    const create = vi.spyOn(videoApi, 'createDownloadUrl').mockResolvedValue({
      url: 'https://minio.example.test/file',
    });
    const first = renderHook(() => useDownloadUrl('job-1'), { wrapper });
    await expect(first.result.current.request()).resolves.toEqual({
      url: 'https://minio.example.test/file',
      expiresAt: null,
    });
    expect(create).toHaveBeenCalledWith('job-1');

    create.mockResolvedValue({ url: 'javascript:alert(1)' });
    const malformed = renderHook(() => useDownloadUrl('job-2'), { wrapper });
    await expect(malformed.result.current.request()).rejects.toThrow(
      'DOWNLOAD_URL_INVALID',
    );
    const missing = renderHook(() => useDownloadUrl(undefined), { wrapper });
    await expect(missing.result.current.request()).rejects.toThrow(
      'JOB_ID_MISSING',
    );
  });

  it('exposes normalized Problem Details when URL issuance fails', async () => {
    vi.spyOn(videoApi, 'createDownloadUrl').mockRejectedValue({ status: 503 });
    const { result } = renderHook(() => useDownloadUrl('job-1'), { wrapper });
    await expect(result.current.request()).rejects.toMatchObject({
      status: 503,
    });
    await waitFor(() => expect(result.current.problem?.status).toBe(503));
  });

  it('keeps signed URL navigation private', () => {
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    openDownloadUrl('https://minio.example.test/signed/path');
    expect(click).toHaveBeenCalled();
  });
});
