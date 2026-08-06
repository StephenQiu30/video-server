import {
  cancelDownloadApiV1DownloadsJobIdCancelPost,
  createDownloadApiV1DownloadsPost,
  getDownloadApiV1DownloadsJobIdGet,
  issueDownloadUrlApiV1DownloadsJobIdDownloadUrlPost,
} from '@/api/downloads';
import {
  getInspectionApiV1InspectionsInspectionIdGet,
  inspectMediaApiV1InspectionsPost,
} from '@/api/inspections';
import type { DownloadJob, DownloadUrl, Inspection } from './types';

export {
  ApiError,
  createIdempotencyKey,
  displayError,
} from '@/shared/api/request';

export function inspectMedia(url: string, key: string): Promise<Inspection> {
  return inspectMediaApiV1InspectionsPost(
    { url },
    { headers: { 'Idempotency-Key': key } },
  );
}

export function getInspection(id: string): Promise<Inspection> {
  return getInspectionApiV1InspectionsInspectionIdGet({ inspection_id: id });
}

export function createDownload(
  inspectionId: string,
  formatId: string,
  key: string,
): Promise<DownloadJob> {
  return createDownloadApiV1DownloadsPost(
    { inspection_id: inspectionId, format_id: formatId },
    { headers: { 'Idempotency-Key': key } },
  );
}

export function getDownload(id: string): Promise<DownloadJob> {
  return getDownloadApiV1DownloadsJobIdGet({ job_id: id });
}

export function cancelDownload(id: string): Promise<DownloadJob> {
  return cancelDownloadApiV1DownloadsJobIdCancelPost({ job_id: id });
}

export function issueDownloadUrl(id: string): Promise<DownloadUrl> {
  return issueDownloadUrlApiV1DownloadsJobIdDownloadUrlPost({ job_id: id });
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
