import {
  cancelDownload as cancelDownloadRequest,
  createDownload as createDownloadRequest,
  getDownloadHistory as getDownloadHistoryRequest,
  getDownload as getDownloadRequest,
  issueDownloadUrl as issueDownloadUrlRequest,
} from '@/services/video/downloads';
import {
  getInspection as getInspectionRequest,
  inspectMedia as inspectMediaRequest,
} from '@/services/video/inspections';
import type {
  DownloadHistory,
  DownloadHistoryQuery,
  DownloadJob,
  DownloadUrl,
  Inspection,
} from '@/types/video';

export {
  ApiError,
  displayError,
} from '@/requestErrorConfig';
export { createIdempotencyKey } from '@/utils/idempotency';

export function inspectMedia(url: string, key: string): Promise<Inspection> {
  return inspectMediaRequest({ url }, { headers: { 'Idempotency-Key': key } });
}

export function getInspection(id: string): Promise<Inspection> {
  return getInspectionRequest({ inspection_id: id });
}

export function createDownload(
  inspectionId: string,
  formatId: string,
  key: string,
): Promise<DownloadJob> {
  return createDownloadRequest(
    { inspection_id: inspectionId, format_id: formatId },
    { headers: { 'Idempotency-Key': key } },
  );
}

export function getDownload(id: string): Promise<DownloadJob> {
  return getDownloadRequest({ job_id: id });
}

export function getDownloadHistory(
  params: DownloadHistoryQuery,
): Promise<DownloadHistory> {
  return getDownloadHistoryRequest(params);
}

export function cancelDownload(id: string): Promise<DownloadJob> {
  return cancelDownloadRequest({ job_id: id });
}

export function issueDownloadUrl(id: string): Promise<DownloadUrl> {
  return issueDownloadUrlRequest({ job_id: id });
}

export function triggerBrowserDownload(url: string): void {
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = '';
  anchor.rel = 'noopener';
  anchor.target = '_blank';
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
}
