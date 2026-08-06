import { jsonPost, apiRequest as request } from '@/shared/api/client';
import type { DownloadJob, DownloadUrl, Inspection } from './types';

export {
  ApiError,
  createIdempotencyKey,
  displayError,
} from '@/shared/api/client';

export function inspectMedia(url: string, key: string): Promise<Inspection> {
  return request('/inspections', jsonPost({ url }, key));
}

export function getInspection(id: string): Promise<Inspection> {
  return request(`/inspections/${encodeURIComponent(id)}`);
}

export function createDownload(
  inspectionId: string,
  formatId: string,
  key: string,
): Promise<DownloadJob> {
  return request(
    '/downloads',
    jsonPost({ inspection_id: inspectionId, format_id: formatId }, key),
  );
}

export function getDownload(id: string): Promise<DownloadJob> {
  return request(`/downloads/${encodeURIComponent(id)}`);
}

export function cancelDownload(id: string): Promise<DownloadJob> {
  return request(`/downloads/${encodeURIComponent(id)}/cancel`, jsonPost());
}

export function issueDownloadUrl(id: string): Promise<DownloadUrl> {
  return request(
    `/downloads/${encodeURIComponent(id)}/download-url`,
    jsonPost(),
  );
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
