import { useCallback, useEffect, useRef, useState } from 'react';

import { displayError } from '@/lib/request-error';
import { type TaskSocketStatus, taskSocket } from '@/lib/task-socket';
import {
  cancelAnalysis,
  createAnalysis,
  createDocumentAnalysis,
  deleteAnalysis,
  getAnalysis,
  getLatestDocumentAnalysis,
  getLatestDownloadAnalysis,
  retryAnalysis,
} from '@/services/analysis';
import type { AnalysisJob, CreateAnalysisInput } from '@/types/video';
import { terminalAnalysisStatuses } from '@/types/video';
import { createIdempotencyKey } from '@/utils/idempotency';

type Action = 'start' | 'cancel' | 'retry' | 'delete' | null;
type StableKey = { payload: string; value: string };

export function useAnalysisJob(
  inputId: string,
  pollIntervalMs: number,
  inputKind: API.AnalysisInputKind = 'video',
) {
  const [job, setJob] = useState<AnalysisJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [action, setAction] = useState<Action>(null);
  const [socketStatus, setSocketStatus] =
    useState<TaskSocketStatus>('disconnected');
  const sourceKey = `${inputKind}:${inputId}`;
  const createKey = useRef<StableKey | null>(null);
  const retryKey = useRef<StableKey | null>(null);
  const hasLocalJob = useRef(false);
  const sourceKeyRef = useRef(sourceKey);
  const versionRef = useRef(0);

  const analysisId = job?.id ?? null;
  const shouldSync = job ? !terminalAnalysisStatuses.has(job.status) : false;
  versionRef.current = job?.version ?? 0;

  useEffect(() => {
    if (sourceKeyRef.current === sourceKey) return;
    sourceKeyRef.current = sourceKey;
    hasLocalJob.current = false;
    createKey.current = null;
    retryKey.current = null;
    setJob(null);
    setError(null);
  }, [sourceKey]);

  useEffect(() => {
    let disposed = false;
    const loadLatest =
      inputKind === 'screenplay'
        ? getLatestDocumentAnalysis
        : getLatestDownloadAnalysis;
    void loadLatest(inputId)
      .then((current) => {
        if (disposed || hasLocalJob.current || current === null) return;
        hasLocalJob.current = true;
        setJob(current);
      })
      .catch((reason: unknown) => {
        if (!disposed && !hasLocalJob.current) setError(displayError(reason));
      });
    return () => {
      disposed = true;
    };
  }, [inputId, inputKind]);

  useEffect(() => {
    if (!analysisId || !shouldSync) {
      return;
    }
    let disposed = false;
    const refresh = async () => {
      try {
        const current = await getAnalysis(analysisId as string);
        if (disposed) return;
        setJob(current);
        setError(null);
      } catch (reason) {
        if (!disposed) setError(displayError(reason));
      }
    };
    const unsubscribe = taskSocket.subscribe(
      'analysis',
      analysisId,
      versionRef.current,
      () => void refresh(),
      setSocketStatus,
    );
    return () => {
      disposed = true;
      unsubscribe();
    };
  }, [analysisId, shouldSync]);

  useEffect(() => {
    if (!analysisId || !shouldSync || socketStatus !== 'degraded') return;
    const timer = window.setInterval(
      async () => {
        try {
          setJob(await getAnalysis(analysisId));
          setError(null);
        } catch (reason) {
          setError(displayError(reason));
        }
      },
      Math.max(15_000, pollIntervalMs * 10),
    );
    return () => window.clearInterval(timer);
  }, [analysisId, pollIntervalMs, shouldSync, socketStatus]);

  const start = useCallback(
    async (input: CreateAnalysisInput) => {
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
        const create =
          inputKind === 'screenplay' ? createDocumentAnalysis : createAnalysis;
        setJob(await create(inputId, input, createKey.current.value));
      } catch (reason) {
        setError(displayError(reason));
      } finally {
        setAction(null);
      }
    },
    [inputId, inputKind],
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

  const retryPoll = useCallback(async () => {
    setError(null);
    if (!analysisId) return;
    try {
      setJob(await getAnalysis(analysisId));
    } catch (reason) {
      setError(displayError(reason));
    }
  }, [analysisId]);

  const retry = useCallback(async () => {
    if (!analysisId) {
      return;
    }
    if (retryKey.current?.payload !== analysisId) {
      retryKey.current = {
        payload: analysisId,
        value: createIdempotencyKey(),
      };
    }
    setAction('retry');
    setError(null);
    try {
      setJob(await retryAnalysis(analysisId, retryKey.current.value));
      retryKey.current = null;
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setAction(null);
    }
  }, [analysisId]);

  const remove = useCallback(async () => {
    if (!analysisId) return;
    setAction('delete');
    setError(null);
    try {
      await deleteAnalysis(analysisId);
      hasLocalJob.current = false;
      retryKey.current = null;
      setJob(null);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setAction(null);
    }
  }, [analysisId]);

  return {
    action,
    cancel,
    error,
    job,
    remove,
    retry,
    retryPoll,
    socketStatus,
    start,
  };
}
