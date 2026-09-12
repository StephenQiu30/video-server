import { useCallback, useEffect, useRef, useState } from 'react';
import { useRequestScope } from '@/hooks/useRequestScope';

import { type TaskSocketStatus, taskSocket } from '@/lib/task-socket';
import {
  cancelDownload,
  createIdempotencyKey,
  deleteDownload,
  displayError,
  getDownload,
  issueDownloadUrl,
  retryDownload,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadJob } from '@/types/video';
import { terminalDownloadStatuses } from '@/types/video';

type Action = 'cancel' | 'delete' | 'download' | 'retry' | null;
type ErrorKind = 'load' | 'sync' | 'action' | null;

export function useDownloadJob(jobId: string, pollIntervalMs: number) {
  const scope = useRequestScope(jobId);
  const [job, setJob] = useState<DownloadJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ErrorKind>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<Action>(null);
  const [cycle, setCycle] = useState(0);
  const [socketStatus, setSocketStatus] =
    useState<TaskSocketStatus>('disconnected');
  const retryRequest = useRef<{ jobId: string; key: string } | null>(null);
  const versionRef = useRef(0);
  const visibleJob = job?.id === jobId ? job : null;
  const changingJob = job !== null && visibleJob === null;
  versionRef.current = visibleJob?.version ?? 0;
  const jobStatus = visibleJob?.status ?? null;

  const accept = useCallback(
    (next: DownloadJob) => {
      if (next.id !== jobId || next.version < versionRef.current) return false;
      versionRef.current = next.version;
      setJob((current) =>
        mergePresentation(current?.id === next.id ? current : null, next),
      );
      return true;
    },
    [jobId],
  );

  useEffect(() => {
    void cycle;
    let disposed = false;
    setJob(null);
    setAction(null);
    setLoading(true);
    setError(null);
    setErrorKind(null);

    async function load() {
      const request = scope.capture();
      try {
        const current = await getDownload(jobId);
        if (disposed || !request.current()) {
          return;
        }
        accept(current);
        setErrorKind(null);
        setLoading(false);
      } catch (reason) {
        if (!disposed && request.latest()) {
          setError(displayError(reason));
          setErrorKind('load');
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      disposed = true;
    };
  }, [accept, cycle, jobId, scope]);

  useEffect(() => {
    if (action || !jobStatus || terminalDownloadStatuses.has(jobStatus)) return;
    let disposed = false;
    const unsubscribe = taskSocket.subscribe(
      'download',
      jobId,
      versionRef.current,
      async () => {
        const request = scope.capture();
        try {
          const next = await getDownload(jobId);
          if (disposed || !request.current() || !accept(next)) return;
          setError(null);
          setErrorKind(null);
        } catch (reason) {
          if (disposed || !request.latest()) return;
          setError(displayError(reason));
          setErrorKind('sync');
        }
      },
      (status) => {
        if (!disposed) setSocketStatus(status);
      },
    );
    return () => {
      disposed = true;
      unsubscribe();
    };
  }, [accept, action, jobId, jobStatus, scope]);

  useEffect(() => {
    if (action || !jobStatus || terminalDownloadStatuses.has(jobStatus)) return;
    let disposed = false;
    let refreshing = false;
    const refreshState = async () => {
      if (disposed || refreshing) return;
      refreshing = true;
      const request = scope.capture();
      try {
        const current = await getDownload(jobId);
        if (disposed || !request.current() || !accept(current)) return;
        setError(null);
        setErrorKind(null);
      } catch (reason) {
        if (disposed || !request.latest()) return;
        setError(displayError(reason));
        setErrorKind('sync');
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
  }, [accept, action, jobId, jobStatus, pollIntervalMs, scope, socketStatus]);

  const refresh = useCallback(() => {
    scope.invalidate();
    setCycle((current) => current + 1);
  }, [scope]);

  const retry = useCallback(async (): Promise<DownloadJob | null> => {
    scope.invalidate();
    const request = scope.capture();
    setAction('retry');
    setError(null);
    setErrorKind(null);
    if (retryRequest.current?.jobId !== jobId) {
      retryRequest.current = { jobId, key: createIdempotencyKey() };
    }
    try {
      const retried = await retryDownload(jobId, retryRequest.current.key);
      if (!request.current()) return null;
      setJob(retried);
      setErrorKind(null);
      return retried;
    } catch (reason) {
      if (!request.current()) return null;
      setError(displayError(reason));
      setErrorKind('action');
      return null;
    } finally {
      if (request.current()) setAction(null);
    }
  }, [jobId, scope]);

  const cancel = useCallback(async () => {
    scope.invalidate();
    const request = scope.capture();
    setAction('cancel');
    setError(null);
    setErrorKind(null);
    try {
      const cancelled = await cancelDownload(jobId);
      if (!request.current() || !accept(cancelled)) return;
      setErrorKind(null);
    } catch (reason) {
      if (!request.current()) return;
      setError(displayError(reason));
      setErrorKind('action');
    } finally {
      if (request.current()) setAction(null);
    }
  }, [accept, jobId, scope]);

  const download = useCallback(async () => {
    scope.invalidate();
    const request = scope.capture();
    setAction('download');
    setError(null);
    setErrorKind(null);
    try {
      const result = await issueDownloadUrl(jobId);
      if (!request.current()) return;
      triggerBrowserDownload(result.url, result.filename);
      setErrorKind(null);
    } catch (reason) {
      if (!request.current()) return;
      setError(displayError(reason));
      setErrorKind('action');
    } finally {
      if (request.current()) setAction(null);
    }
  }, [jobId, scope]);

  const remove = useCallback(async (): Promise<boolean> => {
    scope.invalidate();
    const request = scope.capture();
    setAction('delete');
    setError(null);
    setErrorKind(null);
    try {
      await deleteDownload(jobId);
      if (!request.current()) return false;
      setJob(null);
      return true;
    } catch (reason) {
      if (!request.current()) return false;
      setError(displayError(reason));
      setErrorKind('action');
      return false;
    } finally {
      if (request.current()) setAction(null);
    }
  }, [jobId, scope]);

  return {
    action,
    cancel,
    download,
    error,
    errorKind,
    job: visibleJob,
    loading: loading || changingJob,
    remove,
    refresh,
    retry,
    socketStatus,
  };
}

function mergePresentation(
  current: DownloadJob | null,
  next: DownloadJob,
): DownloadJob {
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
