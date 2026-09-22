import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import { privateQueryKey } from '@/lib/query-keys';
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
  const queries = useQueryClient();
  const [actionError, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [socketStatus, setSocketStatus] =
    useState<TaskSocketStatus>('disconnected');
  const sourceKey = `${inputKind}:${inputId}`;
  const queryKey = useMemo(
    () => privateQueryKey('analysis', inputKind, inputId),
    [inputKind, inputId],
  );
  const scope = useRequestScope(sourceKey);
  const createKey = useRef<StableKey | null>(null);
  const retryKey = useRef<StableKey | null>(null);
  const sourceKeyRef = useRef(sourceKey);
  const versionRef = useRef(0);

  const snapshot = useQuery({
    queryKey,
    enabled: !action,
    queryFn: async ({ signal }) => {
      const previous = queries.getQueryData<API.AnalysisResponse | null>(
        queryKey,
      );
      const active = previous && !terminalAnalysisStatuses.has(previous.status);
      const next = active
        ? await getAnalysis(
            { analysis_id: encodeURIComponent(previous.id) },
            { signal },
          )
        : inputKind === 'screenplay'
          ? await getLatestDocumentAnalysis(
              { document_id: encodeURIComponent(inputId) },
              { signal },
            )
          : await getLatestDownloadAnalysis(
              { download_id: encodeURIComponent(inputId) },
              { signal },
            );
      if (active && next?.id !== previous.id)
        throw new Error('Unexpected analysis response');
      const current = queries.getQueryData<API.AnalysisResponse | null>(
        queryKey,
      );
      return current && next && isOlder(current, next) ? current : next;
    },
    refetchInterval: (query) => {
      const current = query.state.data;
      if (
        !current ||
        query.state.error ||
        terminalAnalysisStatuses.has(current.status)
      )
        return false;
      return socketStatus === 'connected'
        ? Math.max(15_000, pollIntervalMs * 10)
        : Math.max(2_000, pollIntervalMs);
    },
    refetchOnWindowFocus: true,
  });
  const job = snapshot.data ?? null;
  const error =
    actionError ?? (snapshot.error ? displayError(snapshot.error) : null);
  const accept = useCallback(
    (next: API.AnalysisResponse) => {
      const current = queries.getQueryData<API.AnalysisResponse | null>(
        queryKey,
      );
      if (current && isOlder(current, next)) return false;
      queries.setQueryData(queryKey, next);
      return true;
    },
    [queries, queryKey],
  );
  const analysisId = job?.id ?? null;
  const shouldSync = job ? !terminalAnalysisStatuses.has(job.status) : false;
  versionRef.current = job?.version ?? 0;

  useEffect(() => {
    if (sourceKeyRef.current === sourceKey) return;
    sourceKeyRef.current = sourceKey;
    createKey.current = null;
    retryKey.current = null;
    setError(null);
    setAction(null);
    setSocketStatus('disconnected');
  }, [sourceKey]);

  const refetch = snapshot.refetch;
  useEffect(() => {
    if (action || !analysisId || !shouldSync) return;
    return taskSocket.subscribe(
      'analysis',
      analysisId,
      versionRef.current,
      () => {
        void refetch({ cancelRefetch: false });
      },
      setSocketStatus,
    );
  }, [action, analysisId, refetch, shouldSync]);

  const start = useCallback(
    async (input: API.AnalysisRequest) => {
      scope.invalidate();
      const request = scope.capture();
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
        await queries.cancelQueries({ queryKey });
        if (!request.current()) return;
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
        else void queries.invalidateQueries({ queryKey });
      }
    },
    [accept, inputId, inputKind, queries, queryKey, scope],
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
      await queries.cancelQueries({ queryKey });
      if (!request.current()) return;
      const next = await cancelAnalysis({
        analysis_id: encodeURIComponent(analysisId),
      });
      if (request.current()) accept(next);
    } catch (reason) {
      if (request.current()) setError(displayError(reason));
    } finally {
      if (request.current()) setAction(null);
      else void queries.invalidateQueries({ queryKey });
    }
  }, [accept, analysisId, queries, queryKey, scope]);

  const retryPoll = useCallback(async () => {
    setError(null);
    await refetch({ cancelRefetch: false });
  }, [refetch]);

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
      await queries.cancelQueries({ queryKey });
      if (!request.current()) return;
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
      else void queries.invalidateQueries({ queryKey });
    }
  }, [accept, analysisId, queries, queryKey, scope]);

  const remove = useCallback(async () => {
    if (!analysisId) return;
    scope.invalidate();
    const request = scope.capture();
    setAction('delete');
    setError(null);
    try {
      await queries.cancelQueries({ queryKey });
      if (!request.current()) return;
      await deleteAnalysis({ analysis_id: encodeURIComponent(analysisId) });
      if (!request.current()) return;
      createKey.current = null;
      retryKey.current = null;
      queries.setQueryData(queryKey, null);
    } catch (reason) {
      if (request.current()) setError(displayError(reason));
    } finally {
      if (request.current()) setAction(null);
      else void queries.invalidateQueries({ queryKey });
    }
  }, [analysisId, queries, queryKey, scope]);

  return {
    action,
    cancel,
    error,
    errorKind: actionError
      ? 'action'
      : snapshot.error
        ? job
          ? 'sync'
          : 'load'
        : null,
    job,
    loading: snapshot.isPending,
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

function isOlder(current: API.AnalysisResponse, next: API.AnalysisResponse) {
  return (
    current.id === next.id &&
    (next.version < current.version || next.run_no < current.run_no)
  );
}
