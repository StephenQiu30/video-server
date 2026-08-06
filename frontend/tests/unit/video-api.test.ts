import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  ApiError,
  cancelDownload,
  createDownload,
  createIdempotencyKey,
  displayError,
  getDownload,
  getInspection,
  inspectMedia,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/features/download/api';
import { inspection, job, jsonResponse } from './download-fixtures';

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('download API', () => {
  it('uses same-origin endpoints and idempotency headers', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(inspection, 201))
      .mockResolvedValueOnce(jsonResponse(job(), 202));
    vi.stubGlobal('fetch', fetchMock);

    await inspectMedia('https://media.example/owned', 'inspect-key');
    await createDownload(
      inspection.id,
      inspection.formats[0].id,
      'download-key',
    );

    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/inspections');
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      credentials: 'same-origin',
      method: 'POST',
      headers: expect.objectContaining({ 'Idempotency-Key': 'inspect-key' }),
    });
    expect(fetchMock.mock.calls[1][0]).toBe('/api/v1/downloads');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      headers: expect.objectContaining({ 'Idempotency-Key': 'download-key' }),
    });
  });

  it('covers query, cancel, and download-url endpoints', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(inspection))
      .mockResolvedValueOnce(jsonResponse(job('running')))
      .mockResolvedValueOnce(jsonResponse(job('cancelled')))
      .mockResolvedValueOnce(
        jsonResponse({
          url: 'https://objects.example/token',
          expires_at: '2026-08-06T10:05:00Z',
        }),
      );
    vi.stubGlobal('fetch', fetchMock);

    await getInspection(inspection.id);
    await getDownload(job().id);
    await cancelDownload(job().id);
    await issueDownloadUrl(job().id);

    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      `/api/v1/inspections/${inspection.id}`,
      `/api/v1/downloads/${job().id}`,
      `/api/v1/downloads/${job().id}/cancel`,
      `/api/v1/downloads/${job().id}/download-url`,
    ]);
    expect(fetchMock.mock.calls[2][1]).toMatchObject({ method: 'POST' });
  });

  it('parses RFC9457 and fallback errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(
          jsonResponse(
            {
              status: 409,
              code: 'idempotency_conflict',
              title: 'Idempotency conflict',
              detail: '请勿将同一请求键用于其他地址。',
            },
            409,
          ),
        )
        .mockResolvedValueOnce(new Response('bad gateway', { status: 502 })),
    );

    await expect(
      inspectMedia('https://example.com/a', 'key'),
    ).rejects.toMatchObject({
      code: 'idempotency_conflict',
      status: 409,
    });
    await expect(getDownload(job().id)).rejects.toEqual(
      new ApiError(
        502,
        'request_failed',
        '请求失败',
        '服务暂时不可用，请稍后重试。',
      ),
    );
  });

  it('uses safe fallbacks for partial problems and unknown errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ title: 'Incomplete' }, 500)),
    );

    await expect(getDownload(job().id)).rejects.toMatchObject({
      code: 'request_failed',
    });
    expect(displayError(new Error('secret upstream detail'))).toBe(
      '发生未知错误，请稍后重试。',
    );
  });

  it('creates random keys and triggers a browser download', () => {
    const randomUUID = vi.fn().mockReturnValue('random-id');
    vi.stubGlobal('crypto', { randomUUID });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {});

    expect(createIdempotencyKey()).toBe('random-id');
    triggerBrowserDownload('https://objects.example/token');

    expect(randomUUID).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(document.querySelector('a[download]')).not.toBeInTheDocument();
  });
});
