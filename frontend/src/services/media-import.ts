import {
  hashFileSha256,
  MediaTransferError,
  uploadMultipartFile,
} from '@/lib/media-upload';
import { displayError } from '@/lib/request-error';
import { cancelDownload as cancelDownloadRequest } from '@/services/video/downloads';
import {
  completeMediaImport as completeMediaImportRequest,
  createMediaImport as createMediaImportRequest,
  createMediaUploadSession as createMediaUploadSessionRequest,
} from '@/services/video/mediaImports';

export type MediaImportPhase =
  | 'idle'
  | 'hashing'
  | 'creating'
  | 'uploading'
  | 'completing'
  | 'cancelling';

export type MediaImportObserver = {
  onPhase: (phase: MediaImportPhase) => void;
  onProgress: (percentage: number) => void;
  onResource: (resourceId: string) => void;
};

export function validateLocalVideo(file: File): string | null {
  if (file.size <= 0) return '请选择包含内容的 MP4 视频。';
  if (!file.name.toLocaleLowerCase('en-US').endsWith('.mp4')) {
    return '当前只支持上传 MP4 视频。';
  }
  if (file.type && file.type.toLocaleLowerCase('en-US') !== 'video/mp4') {
    return '文件类型与 MP4 不一致，请重新选择。';
  }
  return null;
}

export async function importLocalVideo(
  file: File,
  idempotencyKey: string,
  observer: MediaImportObserver,
  signal: AbortSignal,
  declaredOrigin: API.DeclaredOrigin = 'user_file',
): Promise<API.MediaImportResponse> {
  observer.onPhase('hashing');
  observer.onProgress(0);
  const declaredSha256 = await hashFileSha256(
    file,
    observer.onProgress,
    signal,
  );

  observer.onPhase('creating');
  const resource = await createMediaImportRequest(
    {
      file_name: file.name,
      declared_size_bytes: file.size,
      declared_sha256: declaredSha256,
      rights_accepted: true,
      declared_origin: declaredOrigin,
    },
    { headers: { 'Idempotency-Key': idempotencyKey } },
  );
  observer.onResource(resource.id);

  const session = await createMediaUploadSessionRequest({
    resource_id: encodeURIComponent(resource.id),
  });
  if (session.resource_id !== resource.id) {
    throw new MediaTransferError('上传会话与导入任务不匹配，请重新开始上传。');
  }
  observer.onPhase('uploading');
  observer.onProgress(0);
  const parts = await uploadMultipartFile(
    file,
    session,
    observer.onProgress,
    signal,
  );

  observer.onPhase('completing');
  observer.onProgress(100);
  return completeMediaImportRequest(
    { resource_id: encodeURIComponent(resource.id) },
    { parts },
  );
}

export async function cancelLocalVideoImport(
  resourceId: string,
): Promise<void> {
  await cancelDownloadRequest({ job_id: encodeURIComponent(resourceId) });
}

export function displayMediaImportError(error: unknown): string {
  return error instanceof MediaTransferError
    ? error.message
    : displayError(error);
}

export function isMediaImportAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}
