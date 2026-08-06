import { useCallback, useEffect, useState } from 'react';

import {
  cancelDownload,
  displayError,
  getDownload,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/features/download/api';
import type { DownloadJob } from '@/features/download/types';
import { terminalStatuses } from '@/features/download/types';

type Action = 'cancel' | 'download' | null;

export function useDownloadJob(jobId: string, pollIntervalMs: number) {
  const [job, setJob] = useState<DownloadJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<Action>(null);
  const [cycle, setCycle] = useState(0);

  // biome-ignore lint/correctness/useExhaustiveDependencies: cycle is the explicit retry trigger.
  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    setLoading(true);
    setError(null);

    async function poll() {
      try {
        const current = await getDownload(jobId);
        if (disposed) {
          return;
        }
        setJob(current);
        setLoading(false);
        if (!terminalStatuses.has(current.status)) {
          timer = window.setTimeout(poll, pollIntervalMs);
        }
      } catch (reason) {
        if (!disposed) {
          setError(displayError(reason));
          setLoading(false);
        }
      }
    }

    void poll();
    return () => {
      disposed = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [cycle, jobId, pollIntervalMs]);

  const retry = useCallback(() => {
    setCycle((current) => current + 1);
  }, []);

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

  return { action, cancel, download, error, job, loading, retry };
}
