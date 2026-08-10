import { useCallback, useEffect, useRef, useState } from 'react';

import { displayError } from '@/lib/request-error';
import {
  cancelAnalysis,
  createAnalysis,
  getAnalysis,
} from '@/services/analysis';
import type { AnalysisJob, CreateAnalysisInput } from '@/types/video';
import { terminalAnalysisStatuses } from '@/types/video';
import { createIdempotencyKey } from '@/utils/idempotency';

type Action = 'start' | 'cancel' | null;
type StableKey = { payload: string; value: string };

export function useAnalysisJob(downloadId: string, pollIntervalMs: number) {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [pollCycle, setPollCycle] = useState(0);
  const createKey = useRef<StableKey | null>(null);

  const analysisId = job?.id ?? null;
  const shouldPoll = job ? !terminalAnalysisStatuses.has(job.status) : false;

  useEffect(() => {
    void pollCycle;
    if (!analysisId || !shouldPoll) {
      return;
    }

    let disposed = false;
    let timer: number | undefined;

    async function poll() {
      try {
        const current = await getAnalysis(analysisId as string);
        if (disposed) {
          return;
        }
        setJob(current);
        setError(null);
        if (!terminalAnalysisStatuses.has(current.status)) {
          timer = window.setTimeout(poll, pollIntervalMs);
        }
      } catch (reason) {
        if (!disposed) {
          setError(displayError(reason));
        }
      }
    }

    timer = window.setTimeout(poll, pollIntervalMs);
    return () => {
      disposed = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [analysisId, pollCycle, pollIntervalMs, shouldPoll]);

  const start = useCallback(
    async (input: CreateAnalysisInput) => {
      const payload = JSON.stringify([downloadId, input]);
      if (createKey.current?.payload !== payload) {
        createKey.current = {
          payload,
          value: createIdempotencyKey(),
        };
      }

      setAction('start');
      setError(null);
      try {
        setJob(
          await createAnalysis(downloadId, input, createKey.current.value),
        );
      } catch (reason) {
        setError(displayError(reason));
      } finally {
        setAction(null);
      }
    },
    [downloadId],
  );

  const cancel = useCallback(async () => {
    if (!analysisId) {
      return;
    }
    setAction('cancel');
    setError(null);
    try {
      setJob(await cancelAnalysis(analysisId));
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setAction(null);
    }
  }, [analysisId]);

  const retryPoll = useCallback(() => {
    setError(null);
    setPollCycle((current) => current + 1);
  }, []);

  const restart = useCallback(() => {
    createKey.current = null;
    setError(null);
    setJob(null);
  }, []);

  return {
    action,
    cancel,
    error,
    job,
    restart,
    retryPoll,
    start,
  };
}
