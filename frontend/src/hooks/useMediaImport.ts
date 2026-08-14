import { useCallback, useRef, useState } from 'react';

import {
  cancelLocalVideoImport,
  displayMediaImportError,
  importLocalVideo,
  isMediaImportAbort,
  type MediaImportPhase,
  validateLocalVideo,
} from '@/services/media-import';
import { createIdempotencyKey } from '@/utils/idempotency';

type ActiveRun = {
  controller: AbortController;
  resourceId: string | null;
};

type StableKey = { payload: string; value: string };

export function useMediaImport(onComplete: (downloadId: string) => void) {
  const [file, setFile] = useState<File | null>(null);
  const [rightsAccepted, setRightsAcceptedState] = useState(false);
  const [phase, setPhase] = useState<MediaImportPhase>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [invalidField, setInvalidField] = useState<'file' | 'rights' | null>(
    null,
  );
  const activeRef = useRef<ActiveRun | null>(null);
  const keyRef = useRef<StableKey | null>(null);

  const selectFile = useCallback((next: File | null) => {
    setFile(next);
    setNotice(null);
    setInvalidField(null);
    keyRef.current = null;
    if (!next) {
      setError(null);
      return;
    }
    const validationError = validateLocalVideo(next);
    setError(validationError);
    if (validationError) setInvalidField('file');
  }, []);

  const setRightsAccepted = useCallback((accepted: boolean) => {
    setRightsAcceptedState(accepted);
    if (accepted) {
      setInvalidField((current) => (current === 'rights' ? null : current));
      setError((current) =>
        current === '请确认你有权上传并分析这个视频。' ? null : current,
      );
    }
  }, []);

  const start = useCallback(async () => {
    if (!file) {
      setInvalidField('file');
      setError('请先选择一个 MP4 视频。');
      return;
    }
    const validationError = validateLocalVideo(file);
    if (validationError) {
      setInvalidField('file');
      setError(validationError);
      return;
    }
    if (!rightsAccepted) {
      setInvalidField('rights');
      setError('请确认你有权上传并分析这个视频。');
      return;
    }

    const run: ActiveRun = {
      controller: new AbortController(),
      resourceId: null,
    };
    activeRef.current = run;
    setError(null);
    setNotice(null);
    setInvalidField(null);
    try {
      const payload = `${file.name}:${file.size}:${file.lastModified}:${file.type}`;
      if (keyRef.current?.payload !== payload) {
        keyRef.current = { payload, value: createIdempotencyKey() };
      }
      const result = await importLocalVideo(
        file,
        keyRef.current.value,
        {
          onPhase: (next) => {
            if (activeRef.current === run) setPhase(next);
          },
          onProgress: (next) => {
            if (activeRef.current === run) setProgress(next);
          },
          onResource: (resourceId) => {
            run.resourceId = resourceId;
          },
        },
        run.controller.signal,
      );
      if (activeRef.current === run) onComplete(result.download_id);
    } catch (reason) {
      if (activeRef.current === run && !isMediaImportAbort(reason)) {
        setError(displayMediaImportError(reason));
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
    setPhase(active.resourceId ? 'cancelling' : 'idle');
    try {
      if (active.resourceId) await cancelLocalVideoImport(active.resourceId);
      setNotice('上传已取消，未完成的分片将由服务端清理。');
      keyRef.current = null;
    } catch (reason) {
      setError(displayMediaImportError(reason));
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
    notice,
    phase,
    progress,
    rightsAccepted,
    rightsInvalid: invalidField === 'rights',
    selectFile,
    setRightsAccepted,
    start,
  };
}
