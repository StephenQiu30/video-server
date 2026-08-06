import { request } from '@/shared/api/client';
import type { DownloadJob, DownloadUrl, Inspection } from './types';

export {
  ApiError,
  createIdempotencyKey,
  displayError,
} from '@/shared/api/client';

export function inspectMedia(url: string, key: string): Promise<Inspection> {
  return request('/api/v1/inspections', {
    method: 'POST',
    headers: { 'Idempotency-Key': key },
    data: { url },
  });
}

export function getInspection(id: string): Promise<Inspection> {
  return request(`/api/v1/inspections/${encodeURIComponent(id)}`);
}

export function createDownload(
  inspectionId: string,
  formatId: string,
  key: string,
): Promise<DownloadJob> {
  return request('/api/v1/downloads', {
    method: 'POST',
    headers: { 'Idempotency-Key': key },
    data: { inspection_id: inspectionId, format_id: formatId },
  });
}

export function getDownload(id: string): Promise<DownloadJob> {
  return request(`/api/v1/downloads/${encodeURIComponent(id)}`);
}

export function cancelDownload(id: string): Promise<DownloadJob> {
  return request(`/api/v1/downloads/${encodeURIComponent(id)}/cancel`, {
    method: 'POST',
  });
}

export function issueDownloadUrl(id: string): Promise<DownloadUrl> {
  return request(`/api/v1/downloads/${encodeURIComponent(id)}/download-url`, {
    method: 'POST',
  });
}

export function triggerBrowserDownload(url: string): void {
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = '';
  anchor.rel = 'noopener';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
}
