import {
  deleteDocument,
  getDocumentImport,
  listDocuments,
} from '@/services/video/documents';
import type {
  ScreenplayDocument,
  ScreenplayDocumentPage,
  ScreenplayDocumentQuery,
} from '@/types/video';

export { displayError } from '@/lib/request-error';

export function listScreenplayDocuments(
  params: ScreenplayDocumentQuery,
): Promise<ScreenplayDocumentPage> {
  return listDocuments(params);
}

export function getScreenplayDocument(
  documentId: string,
): Promise<ScreenplayDocument> {
  return getDocumentImport({ document_id: encodeURIComponent(documentId) });
}

export function deleteScreenplayDocument(documentId: string): Promise<void> {
  return deleteDocument({ document_id: encodeURIComponent(documentId) });
}
