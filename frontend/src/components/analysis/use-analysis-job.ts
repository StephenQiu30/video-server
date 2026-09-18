import { useCallback, useEffect, useRef, useState } from 'react';
import {
  cancelAnalysis,
  createAnalysis,
  createDocumentAnalysis,
  deleteAnalysis,
  getAnalysis,
  getLatestDocumentAnalysis,
  getLatestDownloadAnalysis,
  retryAnalysis,
} from '@/api/analyses';
import { useRequestScope } from '@/hooks/use-request-scope';
import { displayError } from '@/lib/request-error';
import { type TaskSocketStatus, taskSocket } from '@/lib/task-socket';

import { createUuid as createIdempotencyKey } from '@/lib/uuid';

type Action = 'start' | 'cancel' | 'retry' | 'delete' | null;
type StableKey = { payload: string; value: string };

export function useAnalysisJob(
  inputId: string,
  pollIntervalMs: number,
  inputKind: API.AnalysisInputKind = 'video',
) {
  const [job, setJob] = useState<API.AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [socketStatus, setSocketStatus] =
    useState<TaskSocketStatus>('disconnected');
  const sourceKey = `${inputKind}:${inputId}`;
  const scope = useRequestScope(sourceKey);
  const createKey = useRef<StableKey | null>(null);
  const retryKey = useRef<StableKey | null>(null);
  const hasLocalJob = useRef(false);
  const sourceKeyRef = useRef(sourceKey);
  const versionRef = useRef(0);
  const snapshotRef = useRef<API.AnalysisResponse | null>(null);

  const accept = useCallback((next: API.AnalysisResponse) => {
    const current = snapshotRef.current;
    if (
      current?.id === next.id &&
      (next.version < current.version || next.run_no < current.run_no)
    )
      return false;
    snapshotRef.current = next;
    setJob(next);
    return true;
  }, []);

  const analysisId = job?.id ?? null;
  const shouldSync = job ? !terminalAnalysisStatuses.has(job.status) : false;
  versionRef.current = job?.version ?? 0;

  useEffect(() => {
    if (sourceKeyRef.current === sourceKey) return;
    sourceKeyRef.current = sourceKey;
    hasLocalJob.current = false;
    createKey.current = null;
    retryKey.current = null;
    snapshotRef.current = null;
    setJob(null);
    setError(null);
    setAction(null);
  }, [sourceKey]);

  useEffect(() => {
    let disposed = false;
    const request = scope.capture();
    const latest =
      inputKind === 'screenplay'
        ? getLatestDocumentAnalysis({
            document_id: encodeURIComponent(inputId),
          })
        : getLatestDownloadAnalysis({
            download_id: encodeURIComponent(inputId),
          });
    void latest
      .then((current) => {
        if (
          disposed ||
          !request.current() ||
          hasLocalJob.current ||
          current === null
        )
          return;
        hasLocalJob.current = true;
        accept(current);
      })
      .catch((reason: unknown) => {
        if (!disposed && request.latest() && !hasLocalJob.current)
          setError(displayError(reason));
      });
    return () => {
      disposed = true;
    };
  }, [accept, inputId, inputKind, scope]);

  useEffect(() => {
    if (action || !analysisId || !shouldSync) {
      return;
    }
    let disposed = false;
    const refresh = async () => {
      const request = scope.capture();
      try {
        const current = await getAnalysis({
          analysis_id: encodeURIComponent(analysisId as string),
        });
        if (
          disposed ||
          !request.current() ||
          current.id !== analysisId ||
          !accept(current)
        )
          return;
        setError(null);
      } catch (reason) {
        if (!disposed && request.latest()) setError(displayError(reason));
      }
    };
    const unsubscribe = taskSocket.subscribe(
      'analysis',
      analysisId,
      versionRef.current,
      () => void refresh(),
      (status) => {
        if (!disposed) setSocketStatus(status);
      },
    );
    return () => {
      disposed = true;
      unsubscribe();
    };
  }, [accept, action, analysisId, scope, shouldSync]);

  useEffect(() => {
    if (action || !analysisId || !shouldSync) return;
    let disposed = false;
    let refreshing = false;
    const refreshState = async () => {
      if (disposed || refreshing) return;
      refreshing = true;
      const request = scope.capture();
      try {
        const current = await getAnalysis({
          analysis_id: encodeURIComponent(analysisId),
        });
        if (
          disposed ||
          !request.current() ||
          current.id !== analysisId ||
          !accept(current)
        )
          return;
        setError(null);
      } catch (reason) {
        if (!disposed && request.latest()) setError(displayError(reason));
      } finally {
        refreshing = false;
      }
    };
    const interval =
      socketStatus === 'connected'
        ? Math.max(15_000, pollIntervalMs * 10)
        : Math.max(2_000, pollIntervalMs);
    const timer = window.setInterval(() => void refreshState(), interval);
    return () => {
      disposed = true;
      window.clearInterval(timer);
    };
  }, [
    accept,
    action,
    analysisId,
    pollIntervalMs,
    scope,
    shouldSync,
    socketStatus,
  ]);

  const start = useCallback(
    async (input: API.AnalysisRequest) => {
      scope.invalidate();
      const request = scope.capture();
      hasLocalJob.current = true;
      const payload = JSON.stringify([inputKind, inputId, input]);
      if (createKey.current?.payload !== payload) {
        createKey.current = {
          payload,
          value: createIdempotencyKey(),
        };
      }

      setAction('start');
      setError(null);
      try {
        const options = {
          headers: { 'Idempotency-Key': createKey.current.value },
        };
        const next =
          inputKind === 'screenplay'
            ? await createDocumentAnalysis(
                { document_id: encodeURIComponent(inputId) },
                input,
                options,
              )
            : await createAnalysis(
                { download_id: encodeURIComponent(inputId) },
                input,
                options,
              );
        if (request.current()) accept(next);
      } catch (reason) {
        if (request.current()) setError(displayError(reason));
      } finally {
        if (request.current()) setAction(null);
      }
    },
    [accept, inputId, inputKind, scope],
  );

  const cancel = useCallback(async () => {
    if (!analysisId) {
      return;
    }
    scope.invalidate();
    const request = scope.capture();
    setAction('cancel');
    setError(null);
    try {
      const next = await cancelAnalysis({
        analysis_id: encodeURIComponent(analysisId),
      });
      if (request.current()) accept(next);
    } catch (reason) {
      if (request.current()) setError(displayError(reason));
    } finally {
      if (request.current()) setAction(null);
    }
  }, [accept, analysisId, scope]);

  const retryPoll = useCallback(async () => {
    setError(null);
    if (!analysisId) return;
    const request = scope.capture();
    try {
      const next = await getAnalysis({
        analysis_id: encodeURIComponent(analysisId),
      });
      if (request.current() && next.id === analysisId) accept(next);
    } catch (reason) {
      if (request.latest()) setError(displayError(reason));
    }
  }, [accept, analysisId, scope]);

  const retry = useCallback(async () => {
    if (!analysisId) {
      return;
    }
    scope.invalidate();
    const request = scope.capture();
    if (retryKey.current?.payload !== analysisId) {
      retryKey.current = {
        payload: analysisId,
        value: createIdempotencyKey(),
      };
    }
    setAction('retry');
    setError(null);
    try {
      const next = await retryAnalysis(
        { analysis_id: encodeURIComponent(analysisId) },
        { headers: { 'Idempotency-Key': retryKey.current.value } },
      );
      if (!request.current()) return;
      accept(next);
      retryKey.current = null;
    } catch (reason) {
      if (request.current()) setError(displayError(reason));
    } finally {
      if (request.current()) setAction(null);
    }
  }, [accept, analysisId, scope]);

  const remove = useCallback(async () => {
    if (!analysisId) return;
    scope.invalidate();
    const request = scope.capture();
    setAction('delete');
    setError(null);
    try {
      await deleteAnalysis({ analysis_id: encodeURIComponent(analysisId) });
      if (!request.current()) return;
      hasLocalJob.current = false;
      createKey.current = null;
      retryKey.current = null;
      snapshotRef.current = null;
      setJob(null);
    } catch (reason) {
      if (request.current()) setError(displayError(reason));
    } finally {
      if (request.current()) setAction(null);
    }
  }, [analysisId, scope]);

  return {
    action,
    cancel,
    error,
    job: sourceKeyRef.current === sourceKey ? job : null,
    remove,
    retry,
    retryPoll,
    socketStatus,
    start,
  };
}

const terminalAnalysisStatuses = new Set<API.AnalysisStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
