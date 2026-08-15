import { useCallback, useRef, useState } from 'react';

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
};

type StableKey = { payload: string; value: string };

export function useDocumentImport(onComplete: (documentId: string) => void) {
  const [file, setFile] = useState<File | null>(null);
  const [rightsAccepted, setRightsAcceptedState] = useState(false);
  const [phase, setPhase] = useState<DocumentImportPhase>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [invalidField, setInvalidField] = useState<'file' | 'rights' | null>(
    null,
  );
  const activeRef = useRef<ActiveRun | null>(null);
  const keyRef = useRef<StableKey | null>(null);

  const selectFile = useCallback((next: File | null) => {
    setFile(next);
    setInvalidField(null);
    keyRef.current = null;
    if (!next) {
      setError(null);
      return;
    }
    const validationError = validateScreenplayDocument(next);
    setError(validationError);
    if (validationError) setInvalidField('file');
  }, []);

  const setRightsAccepted = useCallback((accepted: boolean) => {
    setRightsAcceptedState(accepted);
    if (accepted) {
      setInvalidField((current) => (current === 'rights' ? null : current));
      setError((current) =>
        current === '请确认你有权上传并分析这份剧本。' ? null : current,
      );
    }
  }, []);

  const start = useCallback(async () => {
    if (!file) {
      setInvalidField('file');
      setError('请先选择一份剧本文档。');
      return;
    }
    const validationError = validateScreenplayDocument(file);
    if (validationError) {
      setInvalidField('file');
      setError(validationError);
      return;
    }
    if (!rightsAccepted) {
      setInvalidField('rights');
      setError('请确认你有权上传并分析这份剧本。');
      return;
    }

    const run: ActiveRun = {
      controller: new AbortController(),
      documentId: null,
    };
    activeRef.current = run;
    setError(null);
    setInvalidField(null);
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
        setError(displayDocumentImportError(reason));
      }
    } finally {
      if (activeRef.current === run) {
        activeRef.current = null;
        setPhase('idle');
      }
    }
  }, [file, onComplete, rightsAccepted]);

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
    fileInvalid: invalidField === 'file',
    phase,
    progress,
    rightsAccepted,
    rightsInvalid: invalidField === 'rights',
    selectFile,
    setRightsAccepted,
    start,
  };
}
