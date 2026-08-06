import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useInspectFlow } from '@/pages/Download/hooks';
import { videoApi } from '@/utils/videoApi';

const media = {
  id: 'source-1',
  title: '公开演示视频',
  platform: 'example',
  thumbnail_url: null,
  duration_seconds: 90,
  expires_at: new Date(Date.now() + 60_000).toISOString(),
  formats: [
    {
      id: 'format-1',
      label: '720p',
      width: 1280,
      height: 720,
      fps: 30,
      container: 'mp4',
      video_codec: 'h264',
      audio_codec: 'aac',
      estimated_size_bytes: null,
      requires_merge: false,
    },
  ],
};

const format = {
  id: 'format-1',
  label: '720p',
  width: 1280,
  height: 720,
  fps: 30,
  container: 'mp4',
  videoCodec: 'h264',
  audioCodec: 'aac',
  estimatedSizeBytes: null,
  requiresMerge: false,
};

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('Download inspect flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('clears old result and sends one inspect request', async () => {
    const inspect = vi.spyOn(videoApi, 'inspect').mockResolvedValue(media);
    const { result } = renderHook(() => useInspectFlow(), { wrapper });

    await result.current.inspect('https://example.test/video');

    expect(inspect).toHaveBeenCalledTimes(1);
    expect(inspect).toHaveBeenCalledWith(
      { url: 'https://example.test/video' },
      expect.any(Object),
    );
    await waitFor(() => expect(result.current.state).toBe('inspected'));
    expect(result.current.media?.formats[0]?.label).toBe('720p');
  });

  it('sends only the three create contract fields and exposes the returned job id', async () => {
    vi.spyOn(videoApi, 'inspect').mockResolvedValue(media);
    const create = vi
      .spyOn(videoApi, 'createDownload')
      .mockResolvedValue({ id: 'job-1' });
    const { result } = renderHook(() => useInspectFlow(), { wrapper });
    await result.current.inspect('https://example.test/video');
    await waitFor(() => expect(result.current.media?.id).toBe('source-1'));
    const jobId = await result.current.createDownload(
      result.current.media?.formats[0] ?? null,
    );

    expect(jobId).toBe('job-1');
    expect(create).toHaveBeenCalledTimes(1);
    expect(create.mock.calls[0]?.[0]).toEqual({
      source_id: 'source-1',
      format_id: 'format-1',
      client_request_id: expect.any(String),
    });
    expect(Object.keys(create.mock.calls[0]?.[0] ?? {}).sort()).toEqual([
      'client_request_id',
      'format_id',
      'source_id',
    ]);
  });

  it('does not let a stale inspect response replace the newest request', async () => {
    let resolveFirst!: (value: unknown) => void;
    const first = new Promise((resolve) => {
      resolveFirst = resolve;
    });
    const second = Promise.resolve({ ...media, id: 'source-2' });
    vi.spyOn(videoApi, 'inspect')
      .mockReturnValueOnce(first)
      .mockReturnValueOnce(second);
    const { result } = renderHook(() => useInspectFlow(), { wrapper });
    const firstRequest = result.current.inspect('https://example.test/first');
    await result.current.inspect('https://example.test/second');
    resolveFirst({ ...media, id: 'source-1' });
    await firstRequest;

    await waitFor(() => expect(result.current.media?.id).toBe('source-2'));
  });

  it('exposes recoverable inspect and create failures and expiry', async () => {
    const inspect = vi
      .spyOn(videoApi, 'inspect')
      .mockRejectedValue({ status: 502 });
    const { result } = renderHook(() => useInspectFlow(), { wrapper });
    await result.current.inspect('https://example.test/video');
    await waitFor(() => expect(result.current.state).toBe('inspect_failed'));
    expect(result.current.problem?.status).toBe(502);
    inspect.mockResolvedValue({
      ...media,
      expires_at: new Date(Date.now() - 1).toISOString(),
    });
    await result.current.inspect('https://example.test/expired');
    await waitFor(() => expect(result.current.state).toBe('expired'));
    await expect(result.current.createDownload(format)).resolves.toBeNull();
  });

  it('rejects malformed inspect/create responses and guards missing formats', async () => {
    const inspect = vi.spyOn(videoApi, 'inspect').mockResolvedValue({});
    const { result } = renderHook(() => useInspectFlow(), { wrapper });
    await result.current.inspect('https://example.test/video');
    await waitFor(() => expect(result.current.state).toBe('inspect_failed'));
    inspect.mockResolvedValue(media);
    await result.current.inspect('https://example.test/video');
    await waitFor(() => expect(result.current.state).toBe('inspected'));
    expect(await result.current.createDownload(null)).toBeNull();
    vi.spyOn(videoApi, 'createDownload').mockResolvedValue({});
    expect(await result.current.createDownload(format)).toBeNull();
    await waitFor(() => expect(result.current.createProblem).not.toBeNull());
  });

  it('does not issue duplicate create mutations while one is pending', async () => {
    let resolve!: (value: unknown) => void;
    vi.spyOn(videoApi, 'inspect').mockResolvedValue(media);
    const create = vi.spyOn(videoApi, 'createDownload').mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    const { result } = renderHook(() => useInspectFlow(), { wrapper });
    await result.current.inspect('https://example.test/video');
    await waitFor(() => expect(result.current.state).toBe('inspected'));
    const first = result.current.createDownload(format);
    await waitFor(() => expect(result.current.isCreating).toBe(true));
    expect(await result.current.createDownload(format)).toBeNull();
    resolve({ id: 'job-1' });
    await expect(first).resolves.toBe('job-1');
    expect(create).toHaveBeenCalledTimes(1);
  });

  it('moves an inspected result to expired when its TTL elapses', async () => {
    vi.useFakeTimers();
    const expiresAt = new Date(Date.now() + 100).toISOString();
    vi.spyOn(videoApi, 'inspect').mockResolvedValue({
      ...media,
      expires_at: expiresAt,
    });
    const { result } = renderHook(() => useInspectFlow(), { wrapper });
    await result.current.inspect('https://example.test/short-lived');
    await vi.waitFor(() => expect(result.current.state).toBe('inspected'));
    vi.advanceTimersByTime(1_100);
    await vi.waitFor(() => expect(result.current.state).toBe('expired'));
    vi.useRealTimers();
  });

  it('uses a non-UUID request ID fallback when crypto UUID is unavailable', async () => {
    const randomUUID = crypto.randomUUID;
    Object.defineProperty(crypto, 'randomUUID', {
      configurable: true,
      value: undefined,
    });
    vi.spyOn(videoApi, 'inspect').mockResolvedValue(media);
    const create = vi
      .spyOn(videoApi, 'createDownload')
      .mockResolvedValue({ id: 'job-1' });
    const { result } = renderHook(() => useInspectFlow(), { wrapper });
    await result.current.inspect('https://example.test/video');
    await waitFor(() => expect(result.current.state).toBe('inspected'));
    await result.current.createDownload(format);
    expect(create.mock.calls[0]?.[0].client_request_id).toMatch(/^[0-9]+-/);
    Object.defineProperty(crypto, 'randomUUID', {
      configurable: true,
      value: randomUUID,
    });
  });
});
