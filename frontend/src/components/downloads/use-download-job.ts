import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  cancelDownload,
  deleteDownload,
  getDownload,
  issueDownloadUrl,
  retryDownload,
} from '@/api/downloads';
import { useRequestScope } from '@/hooks/use-request-scope';
import { triggerBrowserDownload } from '@/lib/browser-download';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';
import { type TaskSocketStatus, taskSocket } from '@/lib/task-socket';

import { createUuid as createIdempotencyKey } from '@/lib/uuid';

type Action = 'cancel' | 'delete' | 'download' | 'retry' | null;
type ErrorKind = 'load' | 'sync' | 'action' | null;

export function useDownloadJob(jobId: string, pollIntervalMs: number) {
  const queries = useQueryClient();
  const scope = useRequestScope(jobId);
  const queryKey = useMemo(() => privateQueryKey('download', jobId), [jobId]);
  const [actionError, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [removedId, setRemovedId] = useState<string | null>(null);
  const [socketStatus, setSocketStatus] =
    useState<TaskSocketStatus>('disconnected');
  const retryRequest = useRef<{ jobId: string; key: string } | null>(null);
  const targetId = useRef(jobId);

  const snapshot = useQuery({
    queryKey,
    enabled: !action && removedId !== jobId,
    queryFn: async ({ signal }) => {
      const next = await getDownload(
        { job_id: encodeURIComponent(jobId) },
        { signal },
      );
      if (next.id !== jobId) throw new Error('Unexpected download response');
      const current = queries.getQueryData<API.DownloadResponse | null>(
        queryKey,
      );
      return current && current.version > next.version
        ? current
        : mergePresentation(current ?? null, next);
    },
    refetchInterval: (query) => {
      const current = query.state.data;
      if (
        !current ||
        query.state.error ||
        terminalDownloadStatuses.has(current.status)
      )
        return false;
      return socketStatus === 'connected'
        ? Math.max(15_000, pollIntervalMs * 10)
        : Math.max(2_000, pollIntervalMs);
    },
    refetchOnWindowFocus: true,
  });
  const job = snapshot.data ?? null;
  const queryError = snapshot.error ? displayError(snapshot.error) : null;
  const error = actionError ?? queryError;
  const errorKind: ErrorKind = actionError
    ? 'action'
    : queryError
      ? job
        ? 'sync'
        : 'load'
      : null;

  const accept = useCallback(
    (next: API.DownloadResponse) => {
      if (next.id !== jobId) return false;
      const current = queries.getQueryData<API.DownloadResponse | null>(
        queryKey,
      );
      if (current && next.version < current.version) return false;
      queries.setQueryData(queryKey, mergePresentation(current ?? null, next));
      return true;
    },
    [jobId, queries, queryKey],
  );

  useEffect(() => {
    if (targetId.current === jobId) return;
    targetId.current = jobId;
    setAction(null);
    setError(null);
    setSocketStatus('disconnected');
    retryRequest.current = null;
  }, [jobId]);

  const snapshotId = job?.id;
  const snapshotVersion = job?.version;
  useEffect(() => {
    if (snapshotId && snapshotVersion !== undefined)
      void queries.invalidateQueries({
        queryKey: privateQueryKey('download-history'),
      });
  }, [snapshotId, snapshotVersion, queries]);

  const refetch = snapshot.refetch;
  const version = useRef(0);
  version.current = job?.version ?? 0;
  const jobStatus = job?.status;
  useEffect(() => {
    if (action || !jobStatus || terminalDownloadStatuses.has(jobStatus)) return;
    return taskSocket.subscribe(
      'download',
      jobId,
      version.current,
      () => {
        // Socket and periodic observation share one query and one active read.
        void refetch({ cancelRefetch: false });
      },
      setSocketStatus,
    );
  }, [action, jobId, jobStatus, refetch]);

  const refresh = useCallback(() => {
    setError(null);
    void refetch({ cancelRefetch: false });
  }, [refetch]);

  const retry = useCallback(async (): Promise<API.DownloadResponse | null> => {
    scope.invalidate();
    const request = scope.capture();
    setAction('retry');
    setError(null);
    if (retryRequest.current?.jobId !== jobId) {
      retryRequest.current = { jobId, key: createIdempotencyKey() };
    }
    try {
      await queries.cancelQueries({ queryKey });
      if (!request.current()) return null;
      const retried = await retryDownload(
        { job_id: encodeURIComponent(jobId) },
        { headers: { 'Idempotency-Key': retryRequest.current.key } },
      );
      if (!request.current()) return null;
      if (retried.id === jobId) accept(retried);
      else
        queries.setQueryData(privateQueryKey('download', retried.id), retried);
      void queries.invalidateQueries({
        queryKey: privateQueryKey('download-history'),
      });
      return retried;
    } catch (reason) {
      if (!request.current()) return null;
      setError(displayError(reason));
      return null;
    } finally {
      if (request.current()) setAction(null);
      else void queries.invalidateQueries({ queryKey });
    }
  }, [accept, jobId, queries, queryKey, scope]);

  const cancel = useCallback(async () => {
    scope.invalidate();
    const request = scope.capture();
    setAction('cancel');
    setError(null);
    try {
      await queries.cancelQueries({ queryKey });
      if (!request.current()) return;
      const cancelled = await cancelDownload({
        job_id: encodeURIComponent(jobId),
      });
      if (!request.current() || !accept(cancelled)) return;
    } catch (reason) {
      if (!request.current()) return;
      setError(displayError(reason));
    } finally {
      if (request.current()) setAction(null);
      else void queries.invalidateQueries({ queryKey });
    }
  }, [accept, jobId, queries, queryKey, scope]);

  const download = useCallback(async () => {
    scope.invalidate();
    const request = scope.capture();
    setAction('download');
    setError(null);
    try {
      const result = await issueDownloadUrl(
        {
          job_id: encodeURIComponent(jobId),
          preview: false,
        },
        {
          headers: { 'X-FrameFetch-Download-Client': 'local-web' },
        },
      );
      if (!request.current()) return;
      triggerBrowserDownload(result.url, result.filename);
    } catch (reason) {
      if (!request.current()) return;
      setError(displayError(reason));
    } finally {
      if (request.current()) setAction(null);
    }
  }, [jobId, scope]);

  const remove = useCallback(async (): Promise<boolean> => {
    scope.invalidate();
    const request = scope.capture();
    setAction('delete');
    setError(null);
    try {
      await queries.cancelQueries({ queryKey });
      if (!request.current()) return false;
      await deleteDownload({ job_id: encodeURIComponent(jobId) });
      if (!request.current()) return false;
      void queries.invalidateQueries({
        queryKey: privateQueryKey('download-history'),
      });
      setRemovedId(jobId);
      queries.setQueryData(queryKey, null);
      return true;
    } catch (reason) {
      if (!request.current()) return false;
      setError(displayError(reason));
      return false;
    } finally {
      if (request.current()) setAction(null);
      else void queries.invalidateQueries({ queryKey });
    }
  }, [jobId, queries, queryKey, scope]);

  return {
    action,
    cancel,
    download,
    error,
    errorKind,
    job,
    loading: snapshot.isPending && removedId !== jobId,
    remove,
    refresh,
    retry,
    socketStatus,
  };
}

function mergePresentation(
  current: API.DownloadResponse | null,
  next: API.DownloadResponse,
): API.DownloadResponse {
  if (!current) return next;
  return {
    ...next,
    title: next.title ?? current.title,
    extractor_key: next.extractor_key ?? current.extractor_key,
    duration_seconds: next.duration_seconds ?? current.duration_seconds,
    thumbnail_url: next.thumbnail_url ?? current.thumbnail_url,
    format: next.format ?? current.format,
  };
}

const terminalDownloadStatuses = new Set<API.DownloadStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
