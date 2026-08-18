import {
  cleanupStoredFiles as cleanupStoredFilesRequest,
  listStoredFiles as listStoredFilesRequest,
} from '@/services/video/admin';

export function listStoredFiles(
  params: API.listStoredFilesParams,
): Promise<API.StoredFileListResponse> {
  return listStoredFilesRequest(params);
}

export function cleanupStoredFiles(
  olderThanDays = 30,
): Promise<API.StorageCleanupResponse> {
  return cleanupStoredFilesRequest({ older_than_days: olderThanDays });
}

export { displayError } from '@/lib/request-error';
