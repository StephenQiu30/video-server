import { MediaTransferError } from '@/lib/media-upload';
import { displayError } from '@/lib/request-error';

export type ImportPhase =
  | 'idle'
  | 'hashing'
  | 'creating'
  | 'uploading'
  | 'completing'
  | 'cancelling';

export type ImportObserver = {
  onPhase: (phase: ImportPhase) => void;
  onProgress: (percentage: number) => void;
  onResource: (resourceId: string) => void;
};

export function displayImportError(error: unknown): string {
  return error instanceof MediaTransferError
    ? error.message
    : displayError(error);
}

export function isImportAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError';
}
