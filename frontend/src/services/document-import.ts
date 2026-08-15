import {
  hashFileSha256,
  MediaTransferError,
  uploadMultipartFile,
} from '@/lib/media-upload';
import { displayError } from '@/lib/request-error';
import {
  cancelDocumentImport,
  completeDocumentImport,
  createDocumentImport,
  createDocumentUploadSession,
} from '@/services/video/documents';

const MAX_DOCUMENT_BYTES = 50 * 1024 * 1024;
const formats = new Map<string, API.DocumentSourceFormat>([
  ['.docx', 'docx'],
  ['.fountain', 'fountain'],
  ['.markdown', 'markdown'],
  ['.md', 'markdown'],
  ['.pdf', 'pdf'],
  ['.txt', 'txt'],
]);

export type DocumentImportPhase =
  | 'idle'
  | 'hashing'
  | 'creating'
  | 'uploading'
  | 'completing'
  | 'cancelling';

export type DocumentImportObserver = {
  onPhase: (phase: DocumentImportPhase) => void;
  onProgress: (percentage: number) => void;
  onResource: (resourceId: string) => void;
};

export function validateScreenplayDocument(file: File): string | null {
  if (file.size <= 0) return '请选择包含内容的剧本文档。';
  if (file.size > MAX_DOCUMENT_BYTES) return '剧本文档不能超过 50 MB。';
  if (!documentSourceFormat(file.name)) {
    return '支持 DOCX、PDF、TXT、Markdown 和 Fountain 文件。';
  }
  return null;
}

export async function importScreenplayDocument(
  file: File,
  idempotencyKey: string,
  observer: DocumentImportObserver,
  signal: AbortSignal,
): Promise<API.DocumentImportResponse> {
  const sourceFormat = documentSourceFormat(file.name);
  const validationError = validateScreenplayDocument(file);
  if (!sourceFormat || validationError) {
    throw new MediaTransferError(validationError ?? '剧本文档格式无效。');
  }

  observer.onPhase('hashing');
  observer.onProgress(0);
  const declaredSha256 = await hashFileSha256(
    file,
    observer.onProgress,
    signal,
  );

  observer.onPhase('creating');
  const resource = await createDocumentImport(
    {
      file_name: file.name,
      source_format: sourceFormat,
      declared_size_bytes: file.size,
      declared_sha256: declaredSha256,
      rights_accepted: true,
    },
    { headers: { 'Idempotency-Key': idempotencyKey } },
  );
  observer.onResource(resource.id);

  const session = await createDocumentUploadSession({
    document_id: encodeURIComponent(resource.id),
  });
  if (session.resource_id !== resource.id) {
    throw new MediaTransferError('上传会话与剧本文档不匹配，请重新开始。');
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
  return completeDocumentImport(
    { document_id: encodeURIComponent(resource.id) },
    { parts },
  );
}

export async function cancelScreenplayDocumentImport(
  documentId: string,
): Promise<void> {
  await cancelDocumentImport({ document_id: encodeURIComponent(documentId) });
}

export function displayDocumentImportError(error: unknown): string {
  return error instanceof MediaTransferError
    ? error.message
    : displayError(error);
}

export function isDocumentImportAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}

function documentSourceFormat(name: string): API.DocumentSourceFormat | null {
  const normalized = name.toLocaleLowerCase('en-US');
  for (const [extension, format] of formats) {
    if (normalized.endsWith(extension)) return format;
  }
  return null;
}
