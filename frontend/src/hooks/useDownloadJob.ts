import { useCallback, useEffect, useRef, useState } from 'react';

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

  useEffect(() => {
    void cycle;
    let disposed = false;
    setJob(null);
    setLoading(true);
    setError(null);
    setErrorKind(null);

    async function load() {
      try {
        const current = await getDownload(jobId);
        if (disposed) {
          return;
        }
        setJob(current);
        setErrorKind(null);
        setLoading(false);
      } catch (reason) {
        if (!disposed) {
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
  }, [cycle, jobId]);

  useEffect(() => {
    if (!jobStatus || terminalDownloadStatuses.has(jobStatus)) return;
    return taskSocket.subscribe(
      'download',
      jobId,
      versionRef.current,
      async () => {
        try {
          setJob(await getDownload(jobId));
          setError(null);
          setErrorKind(null);
        } catch (reason) {
          setError(displayError(reason));
          setErrorKind('sync');
        }
      },
      setSocketStatus,
    );
  }, [jobId, jobStatus]);

  useEffect(() => {
    if (!jobStatus || terminalDownloadStatuses.has(jobStatus)) return;
    let disposed = false;
    let refreshing = false;
    const refreshState = async () => {
      if (disposed || refreshing) return;
      refreshing = true;
      try {
        const current = await getDownload(jobId);
        if (disposed) return;
        setJob(current);
        setError(null);
        setErrorKind(null);
      } catch (reason) {
        if (disposed) return;
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
  }, [jobId, jobStatus, pollIntervalMs, socketStatus]);

  const refresh = useCallback(() => {
    setCycle((current) => current + 1);
  }, []);

  const retry = useCallback(async (): Promise<DownloadJob | null> => {
    setAction('retry');
    setError(null);
    setErrorKind(null);
    if (retryRequest.current?.jobId !== jobId) {
      retryRequest.current = { jobId, key: createIdempotencyKey() };
    }
    try {
      const retried = await retryDownload(jobId, retryRequest.current.key);
      setJob(retried);
      setErrorKind(null);
      return retried;
    } catch (reason) {
      setError(displayError(reason));
      setErrorKind('action');
      return null;
    } finally {
      setAction(null);
    }
  }, [jobId]);

  const cancel = useCallback(async () => {
    setAction('cancel');
    setError(null);
    setErrorKind(null);
    try {
      const cancelled = await cancelDownload(jobId);
      setJob((current) => mergePresentation(current, cancelled));
      setErrorKind(null);
    } catch (reason) {
      setError(displayError(reason));
      setErrorKind('action');
    } finally {
      setAction(null);
    }
  }, [jobId]);

  const download = useCallback(async () => {
    setAction('download');
    setError(null);
    setErrorKind(null);
    try {
      const result = await issueDownloadUrl(jobId);
      triggerBrowserDownload(result.url, result.filename);
      setErrorKind(null);
    } catch (reason) {
      setError(displayError(reason));
      setErrorKind('action');
    } finally {
      setAction(null);
    }
  }, [jobId]);

  const remove = useCallback(async (): Promise<boolean> => {
    setAction('delete');
    setError(null);
    setErrorKind(null);
    try {
      await deleteDownload(jobId);
      return true;
    } catch (reason) {
      setError(displayError(reason));
      setErrorKind('action');
      return false;
    } finally {
      setAction(null);
    }
  }, [jobId]);

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
