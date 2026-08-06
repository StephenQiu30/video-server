import { beforeEach, describe, expect, it, vi } from 'vitest';
import { isNotFoundOrExpired, isTransient, toProblem } from '@/utils/problem';
import { validateVideoUrl } from '@/utils/url';
import { videoApi } from '@/utils/videoApi';
import {
  formatBytes,
  formatDuration,
  isExpired,
  parseDownloadJob,
  parseDownloadUrl,
  parseJobId,
  parseMediaSummary,
} from '@/utils/videoData';

const inspectMedia = vi.fn();
const createDownload = vi.fn();
const getDownload = vi.fn();
const createDownloadUrl = vi.fn();

vi.mock('@/services/video/media', () => ({ inspectMedia }));
vi.mock('@/services/video/downloads', () => ({
  createDownload,
  getDownload,
  createDownloadUrl,
}));

describe('problem details and URL policy', () => {
  it('normalizes nested responses without exposing arbitrary payloads', () => {
    expect(
      toProblem({ response: { status: 503, data: { title: '失败' } } }),
    ).toEqual({
      status: 503,
      code: null,
      title: '失败',
      detail: '服务暂不可用，请稍后重试',
    });
    expect(toProblem({ data: { status: 422, code: 'INVALID' } }).detail).toBe(
      '请求未完成，请检查后重试',
    );
    expect(toProblem({ status: 400, detail: '明确失败' }).detail).toBe(
      '明确失败',
    );
    expect(toProblem(null)).toMatchObject({ status: null, title: '请求失败' });
  });

  it('classifies transient and terminal responses', () => {
    expect(isTransient(undefined)).toBe(true);
    expect(isTransient({ status: 500 })).toBe(true);
    expect(isTransient({ status: 408 })).toBe(true);
    expect(isTransient({ status: 429 })).toBe(true);
    expect(isTransient({ status: 400 })).toBe(false);
    expect(isNotFoundOrExpired({ status: 403 })).toBe(true);
    expect(isNotFoundOrExpired({ status: 404 })).toBe(true);
    expect(isNotFoundOrExpired({ status: 410 })).toBe(true);
    expect(isNotFoundOrExpired({ status: 422 })).toBe(true);
    expect(isNotFoundOrExpired({ status: 500 })).toBe(false);
  });

  it('accepts only bounded HTTP(S) links', () => {
    expect(validateVideoUrl('')).toBe('请输入视频链接');
    expect(validateVideoUrl('   ')).toBe('请输入视频链接');
    expect(validateVideoUrl(`https://${'a'.repeat(2041)}.test`)).toBe(
      '视频链接过长',
    );
    expect(validateVideoUrl('ftp://example.test/video')).toBe(
      '仅支持 HTTP 或 HTTPS 视频链接',
    );
    expect(validateVideoUrl('https://user:password@example.test/video')).toBe(
      '视频链接不能包含账号或密码',
    );
    expect(validateVideoUrl('not a url')).toBe('请输入有效的视频链接');
    expect(validateVideoUrl('https://example.test/video')).toBeNull();
  });
});

describe('video data normalization', () => {
  const expiresAt = new Date(Date.now() + 60_000).toISOString();

  it('normalizes media formats, defaults and rejects malformed entries', () => {
    const result = parseMediaSummary({
      id: 'source',
      expires_at: expiresAt,
      formats: [
        { id: '720', label: '720p', width: 1280, requires_merge: true },
        { id: '', label: 'invalid' },
        null,
      ],
    });
    expect(result).toMatchObject({
      id: 'source',
      title: '未命名视频',
      platform: '未知平台',
      thumbnailUrl: null,
      durationSeconds: null,
    });
    expect(result?.formats).toEqual([
      expect.objectContaining({
        id: '720',
        label: '720p',
        width: 1280,
        height: null,
        requiresMerge: true,
      }),
    ]);
    expect(parseMediaSummary('invalid')).toBeNull();
    expect(
      parseMediaSummary({ id: 'source', expires_at: expiresAt }),
    ).toBeNull();
  });

  it('normalizes jobs, IDs and signed URLs safely', () => {
    expect(
      parseDownloadJob({ id: 'job', status: 'running', progress_percent: 40 }),
    ).toMatchObject({
      id: 'job',
      status: 'running',
      progressPercent: 40,
      stage: null,
    });
    expect(parseDownloadJob({ id: 'job', status: 'unknown' })).toBeNull();
    expect(parseDownloadJob(null)).toBeNull();
    expect(parseJobId({ id: 'job' })).toBe('job');
    expect(parseJobId({ id: 1 })).toBeNull();
    expect(
      parseDownloadUrl({ url: 'http://example.test/file', expires_at: 'x' }),
    ).toEqual({
      url: 'http://example.test/file',
      expiresAt: 'x',
    });
    expect(parseDownloadUrl({ url: 'data:text/plain,secret' })).toBeNull();
    expect(parseDownloadUrl({ url: 'not-url' })).toBeNull();
  });

  it('formats bytes, durations and expiry boundaries', () => {
    expect(formatBytes(-1)).toBe('大小未知');
    expect(formatBytes(0)).toBe('0 B');
    expect(formatBytes(1024)).toBe('1.0 KB');
    expect(formatBytes(10 * 1024)).toBe('10 KB');
    expect(formatBytes(1024 * 1024)).toBe('1.0 MB');
    expect(formatBytes(1024 ** 3)).toBe('1.0 GB');
    expect(formatDuration(null)).toBe('时长未知');
    expect(formatDuration(-1)).toBe('时长未知');
    expect(formatDuration(90.4)).toBe('1:30');
    expect(isExpired('not-a-date')).toBe(true);
    expect(isExpired(new Date(1_000).toISOString(), 1_000)).toBe(true);
    expect(isExpired(new Date(2_000).toISOString(), 1_000)).toBe(false);
  });
});

describe('generated video API adapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    inspectMedia.mockResolvedValue({ id: 'source' });
    createDownload.mockResolvedValue({ id: 'job' });
    getDownload.mockResolvedValue({ id: 'job' });
    createDownloadUrl.mockResolvedValue({ url: 'https://example.test/file' });
  });

  it('routes every operation through generated services with credentials', async () => {
    await videoApi.inspect({ url: 'https://example.test/video' });
    await videoApi.createDownload({
      source_id: 'source',
      format_id: 'format',
      client_request_id: 'request',
    });
    await videoApi.getDownload('job');
    await videoApi.createDownloadUrl('job');
    expect(inspectMedia).toHaveBeenCalledWith(
      { url: 'https://example.test/video' },
      { credentials: 'include' },
    );
    expect(createDownload).toHaveBeenCalledWith(
      {
        source_id: 'source',
        format_id: 'format',
        client_request_id: 'request',
      },
      { credentials: 'include' },
    );
    expect(getDownload).toHaveBeenCalledWith(
      { job_id: 'job' },
      { credentials: 'include' },
    );
    expect(createDownloadUrl).toHaveBeenCalledWith(
      { job_id: 'job' },
      { credentials: 'include' },
    );
  });
});
