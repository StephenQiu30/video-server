import { useCallback, useEffect, useRef, useState } from 'react';

import {
  cancelScreenplayDocumentImport,
  type DocumentImportPhase,
  displayDocumentImportError,
  importScreenplayDocument,
  isDocumentImportAbort,
  validateScreenplayDocument,
} from '@/services/document-import';
import { createIdempotencyKey } from '@/utils/idempotency';

type ActiveRun = {
  controller: AbortController;
  documentId: string | null;
  phase: DocumentImportPhase;
};

type StableKey = { payload: string; value: string };

export function useDocumentImport(onComplete: (documentId: string) => void) {
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<DocumentImportPhase>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [fileInvalid, setFileInvalid] = useState(false);
  const activeRef = useRef<ActiveRun | null>(null);
  const keyRef = useRef<StableKey | null>(null);

  useEffect(
    () => () => {
      const active = activeRef.current;
      activeRef.current = null;
      active?.controller.abort();
    },
    [],
  );

  const selectFile = useCallback((next: File | null) => {
    setFile(next);
    setFileInvalid(false);
    keyRef.current = null;
    if (!next) {
      setError(null);
      return;
    }
    const validationError = validateScreenplayDocument(next);
    setError(validationError);
    if (validationError) setFileInvalid(true);
  }, []);

  const start = useCallback(async () => {
    if (!file) {
      setFileInvalid(true);
      setError('请先选择一份剧本文档。');
      return;
    }
    const validationError = validateScreenplayDocument(file);
    if (validationError) {
      setFileInvalid(true);
      setError(validationError);
      return;
    }

    const run: ActiveRun = {
      controller: new AbortController(),
      documentId: null,
      phase: 'hashing',
    };
    activeRef.current = run;
    setError(null);
    setFileInvalid(false);
    try {
      const payload = `${file.name}:${file.size}:${file.lastModified}:${file.type}`;
      if (keyRef.current?.payload !== payload) {
        keyRef.current = { payload, value: createIdempotencyKey() };
      }
      const result = await importScreenplayDocument(
        file,
        keyRef.current.value,
        {
          onPhase: (next) => {
            run.phase = next;
            if (activeRef.current === run) setPhase(next);
          },
          onProgress: (next) => {
            if (activeRef.current === run) setProgress(next);
          },
          onResource: (documentId) => {
            run.documentId = documentId;
          },
        },
        run.controller.signal,
      );
      if (activeRef.current === run) onComplete(result.id);
    } catch (reason) {
      if (activeRef.current === run && !isDocumentImportAbort(reason)) {
        const message = displayDocumentImportError(reason);
        if (run.documentId && run.phase !== 'completing') {
          setPhase('cancelling');
          try {
            await cancelScreenplayDocumentImport(run.documentId);
            keyRef.current = null;
          } catch {
            // Keep the stable key so a retry can recover the existing resource.
          }
        }
        if (activeRef.current === run) {
          setError(message);
          setProgress(0);
        }
      }
    } finally {
      if (activeRef.current === run) {
        activeRef.current = null;
        setPhase('idle');
      }
    }
  }, [file, onComplete]);

  const cancel = useCallback(async () => {
    const active = activeRef.current;
    if (!active) return;
    activeRef.current = null;
    active.controller.abort();
    setError(null);
    setPhase(active.documentId ? 'cancelling' : 'idle');
    try {
      if (active.documentId) {
        await cancelScreenplayDocumentImport(active.documentId);
      }
      keyRef.current = null;
    } catch (reason) {
      setError(displayDocumentImportError(reason));
    } finally {
      setPhase('idle');
      setProgress(0);
    }
  }, []);

  return {
    busy: phase !== 'idle',
    canCancel: phase === 'hashing' || phase === 'uploading',
    cancel,
    error,
    file,
    fileInvalid,
    phase,
    progress,
    selectFile,
    start,
  };
}
