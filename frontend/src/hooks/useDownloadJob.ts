import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '@/lib/request-error';
import { type TaskSocketStatus, taskSocket } from '@/lib/task-socket';
import {
  cancelDownload,
  createIdempotencyKey,
  displayError,
  getDownload,
  getInspection,
  issueDownloadUrl,
  retryDownload,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadJob, Inspection } from '@/types/video';
import { terminalDownloadStatuses } from '@/types/video';

type Action = 'cancel' | 'download' | 'retry' | null;

export function useDownloadJob(jobId: string, pollIntervalMs: number) {
  const [job, setJob] = useState<DownloadJob | null>(null);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [inspectionError, setInspectionError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<Action>(null);
  const [cycle, setCycle] = useState(0);
  const [socketStatus, setSocketStatus] =
    useState<TaskSocketStatus>('disconnected');
  const retryRequest = useRef<{ jobId: string; key: string } | null>(null);
  const versionRef = useRef(0);
  versionRef.current = job?.version ?? 0;
  const jobStatus = job?.status ?? null;

  useEffect(() => {
    void cycle;
    let disposed = false;
    setLoading(true);
    setError(null);

    async function load() {
      try {
        const current = await getDownload(jobId);
        if (disposed) {
          return;
        }
        setJob(current);
        setLoading(false);
        try {
          const metadata = await getInspection(current.inspection_id);
          if (!disposed) {
            setInspection(metadata);
            setInspectionError(null);
          }
        } catch (reason) {
          if (!disposed) setInspectionError(inspectionFailureMessage(reason));
        }
      } catch (reason) {
        if (!disposed) {
          setError(displayError(reason));
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
        } catch (reason) {
          setError(displayError(reason));
        }
      },
      setSocketStatus,
    );
  }, [jobId, jobStatus]);

  useEffect(() => {
    if (
      !jobStatus ||
      terminalDownloadStatuses.has(jobStatus) ||
      socketStatus !== 'degraded'
    )
      return;
    const timer = window.setInterval(
      async () => {
        try {
          setJob(await getDownload(jobId));
          setError(null);
        } catch (reason) {
          setError(displayError(reason));
        }
      },
      Math.max(15_000, pollIntervalMs * 10),
    );
    return () => window.clearInterval(timer);
  }, [jobId, jobStatus, pollIntervalMs, socketStatus]);

  const refresh = useCallback(() => {
    setCycle((current) => current + 1);
  }, []);

  const retry = useCallback(async (): Promise<DownloadJob | null> => {
    setAction('retry');
    setError(null);
    if (retryRequest.current?.jobId !== jobId) {
      retryRequest.current = { jobId, key: createIdempotencyKey() };
    }
    try {
      const retried = await retryDownload(jobId, retryRequest.current.key);
      setJob(retried);
      return retried;
    } catch (reason) {
      setError(displayError(reason));
      return null;
    } finally {
      setAction(null);
    }
  }, [jobId]);

  const cancel = useCallback(async () => {
    setAction('cancel');
    setError(null);
    try {
      setJob(await cancelDownload(jobId));
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setAction(null);
    }
  }, [jobId]);

  const download = useCallback(async () => {
    setAction('download');
    setError(null);
    try {
      const result = await issueDownloadUrl(jobId);
      triggerBrowserDownload(result.url);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setAction(null);
    }
  }, [jobId]);

  return {
    action,
    cancel,
    download,
    error,
    inspection,
    inspectionError,
    job,
    loading,
    refresh,
    retry,
    socketStatus,
  };
}

function inspectionFailureMessage(reason: unknown): string {
  if (
    reason instanceof ApiError &&
    ['not_found', 'resource_expired'].includes(reason.code)
  ) {
    return '原始媒体信息已过期，下载任务和已生成文件仍可继续使用。';
  }
  return displayError(reason);
}
