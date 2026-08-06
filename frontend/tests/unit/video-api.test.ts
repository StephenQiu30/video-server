import { request } from '@umijs/max';
import { describe, expect, it, vi } from 'vitest';

import {
  cancelDownload,
  createDownload,
  createIdempotencyKey,
  getDownload,
  getInspection,
  inspectMedia,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/services/download';
import { inspection, job } from './download-fixtures';

const requestMock = vi.mocked(request);

describe('download API', () => {
  it('uses same-origin endpoints and idempotency headers', async () => {
    requestMock.mockResolvedValueOnce(inspection).mockResolvedValueOnce(job());

    await inspectMedia('https://media.example/owned', 'inspect-key');
    await createDownload(
      inspection.id,
      inspection.formats[0].id,
      'download-key',
    );

    expect(requestMock).toHaveBeenNthCalledWith(
      1,
      '/api/v1/inspections',
      expect.objectContaining({
        data: { url: 'https://media.example/owned' },
        headers: { 'Idempotency-Key': 'inspect-key' },
        method: 'POST',
      }),
    );
    expect(requestMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/downloads',
      expect.objectContaining({
        data: {
          format_id: inspection.formats[0].id,
          inspection_id: inspection.id,
        },
        headers: { 'Idempotency-Key': 'download-key' },
        method: 'POST',
      }),
    );
  });

  it('covers query, cancel, and download-url endpoints', async () => {
    requestMock
      .mockResolvedValueOnce(inspection)
      .mockResolvedValueOnce(job('running'))
      .mockResolvedValueOnce(job('cancelled'))
      .mockResolvedValueOnce({
        url: 'https://objects.example/token',
        expires_at: '2026-08-06T10:05:00Z',
      });

    await getInspection(inspection.id);
    await getDownload(job().id);
    await cancelDownload(job().id);
    await issueDownloadUrl(job().id);

    expect(requestPaths()).toEqual([
      `/api/v1/inspections/${inspection.id}`,
      `/api/v1/downloads/${job().id}`,
      `/api/v1/downloads/${job().id}/cancel`,
      `/api/v1/downloads/${job().id}/download-url`,
    ]);
    expect(requestMock).toHaveBeenNthCalledWith(
      3,
      `/api/v1/downloads/${job().id}/cancel`,
      expect.objectContaining({ method: 'POST' }),
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

function requestPaths(): string[] {
  return requestMock.mock.calls.map(([path]) => path);
}
