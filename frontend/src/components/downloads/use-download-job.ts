import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getDownload } from '@/api/downloads';
import {
  mergeDownloadPresentation,
  useDownloadActions,
} from '@/components/downloads/use-download-actions';
import { useRequestScope } from '@/hooks/use-request-scope';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';
import { type TaskSocketStatus, taskSocket } from '@/lib/task-socket';

type ErrorKind = 'load' | 'sync' | 'action' | null;

export function useDownloadJob(jobId: string, pollIntervalMs: number) {
  const queries = useQueryClient();
  const scope = useRequestScope(jobId);
  const queryKey = useMemo(() => privateQueryKey('download', jobId), [jobId]);
  const operations = useDownloadActions(jobId);
  const { action, error: actionError, removed } = operations;
  const [socketStatus, setSocketStatus] =
    useState<TaskSocketStatus>('disconnected');
  const targetId = useRef(jobId);

  const snapshot = useQuery<API.DownloadResponse | null>({
    queryKey,
    // A history action can precede the first detail visit. Load the missing
    // snapshot once; mutation completion cancels this read before publishing.
    enabled: (query) => !removed && (!action || query.state.data === undefined),
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
        : mergeDownloadPresentation(current ?? null, next);
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

  useEffect(() => {
    if (targetId.current === jobId) return;
    targetId.current = jobId;
    setSocketStatus('disconnected');
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
    if (!action) void refetch({ cancelRefetch: false });
  }, [action, refetch]);

  const retry = async (): Promise<API.DownloadResponse | null> => {
    const request = scope.capture();
    const result = await operations.execute(jobId, 'retry');
    return request.current() && result?.action === 'retry' ? result.job : null;
  };
  const cancel = async () => {
    await operations.execute(jobId, 'cancel');
  };
  const download = async () => {
    await operations.execute(jobId, 'download');
  };
  const remove = async (): Promise<boolean> => {
    const request = scope.capture();
    const result = await operations.execute(jobId, 'delete');
    return request.current() && result?.action === 'delete';
  };

  return {
    action,
    cancel,
    download,
    error,
    errorKind,
    job,
    loading: snapshot.isPending && !removed,
    removed,
    retryTarget: operations.retryTarget,
    remove,
    refresh,
    retry,
    socketStatus,
  };
}

const terminalDownloadStatuses = new Set<API.DownloadStatus>([
  'succeeded',
  'failed',
  'cancelled',
]);
