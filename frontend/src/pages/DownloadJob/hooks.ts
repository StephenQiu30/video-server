import { useMutation, useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import { isTransient, type ProblemDetails, toProblem } from '@/utils/problem';
import { videoApi } from '@/utils/videoApi';
import {
  type DownloadJob,
  parseDownloadJob,
  parseDownloadUrl,
} from '@/utils/videoData';

const ACTIVE_STATUSES = new Set(['queued', 'running']);

export function isActiveJob(job: DownloadJob | null): boolean {
  return Boolean(job && ACTIVE_STATUSES.has(job.status));
}

export function useDownloadJob(jobId: string | undefined) {
  return useQuery<DownloadJob, unknown>({
    queryKey: ['download', jobId],
    enabled: Boolean(jobId),
    queryFn: async () => {
      const result = parseDownloadJob(
        await videoApi.getDownload(jobId as string),
      );
      if (!result) throw new Error('DOWNLOAD_RESPONSE_INVALID');
      return result;
    },
    retry: (failureCount, error) => failureCount < 2 && isTransient(error),
    refetchInterval: (query) =>
      isActiveJob(query.state.data ?? null) ? 2000 : false,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
    networkMode: 'online',
  });
}

export function useDownloadUrl(jobId: string | undefined) {
  const mutation = useMutation({
    mutationFn: async () => {
      if (!jobId) throw new Error('JOB_ID_MISSING');
      const result = parseDownloadUrl(await videoApi.createDownloadUrl(jobId));
      if (!result) throw new Error('DOWNLOAD_URL_INVALID');
      return result;
    },
    retry: false,
  });
  const request = useCallback(() => {
    if (mutation.isPending) return Promise.resolve(null);
    return mutation.mutateAsync();
  }, [mutation]);
  const problem: ProblemDetails | null = mutation.error
    ? toProblem(mutation.error)
    : null;
  return { ...mutation, request, problem };
}

export function openDownloadUrl(url: string): void {
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.referrerPolicy = 'no-referrer';
  anchor.rel = 'noreferrer';
  anchor.hidden = true;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}
