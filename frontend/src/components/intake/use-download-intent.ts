'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import {
  cancelDownloadIntent,
  createDownloadIntent,
  findDownloadIntent,
  getDownloadIntent,
  refreshDownloadIntent,
} from '@/api/downloadIntents';
import { getInspection } from '@/api/inspections';
import { useAuth } from '@/components/auth/auth-provider';
import { useIntakeDraft } from '@/components/intake/intake-draft-provider';
import { privateQueryKey } from '@/lib/query-keys';
import { ApiError, displayError } from '@/lib/request-error';
import { onSessionGenerationChanged } from '@/lib/session-events';
import { createUuid } from '@/lib/uuid';

const referenceKey = 'framefetch-active-intent';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const terminal = new Set<API.IntentStatus>([
  'ready',
  'handed_off',
  'failed',
  'expired',
  'cancelled',
  'action_required',
]);

export function rememberDownloadIntent(owner: string, id: string) {
  if (!uuid.test(id)) return;
  try {
    sessionStorage.setItem(referenceKey, JSON.stringify({ owner, id }));
  } catch {
    // History can recover the owner-bound resource again when storage returns.
  }
}

export function useDownloadIntent() {
  const { user } = useAuth();
  const { attempt, setAttempt } = useIntakeDraft();
  const queries = useQueryClient();
  const writing = useRef(false);
  const [restored, setRestored] = useState(false);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const intentRoot = privateQueryKey('download-intent');
  const key = [
    ...intentRoot,
    attempt?.id ? 'id' : 'key',
    attempt?.id ?? attempt?.key,
  ];

  function remember(result: API.IntentResponse) {
    const canonical = [...intentRoot, 'id', result.id];
    const current = queries.getQueryData<API.IntentResponse>(canonical);
    const latest =
      current && current.version > result.version ? current : result;
    queries.setQueryData(canonical, latest);
    return latest;
  }

  useEffect(() => {
    if (!user?.id) return;
    try {
      const raw = sessionStorage.getItem(referenceKey);
      if (raw) {
        const saved = JSON.parse(raw);
        const id =
          typeof saved.id === 'string' && uuid.test(saved.id)
            ? saved.id
            : undefined;
        const requestKey =
          typeof saved.key === 'string' && uuid.test(saved.key)
            ? saved.key
            : undefined;
        if (saved.owner === user.id && (id || requestKey)) {
          setAttempt(
            (current) =>
              current ?? {
                ...(id ? { id } : { key: requestKey }),
                input: null,
                submitting: false,
              },
          );
        } else sessionStorage.removeItem(referenceKey);
      }
    } catch {
      // Storage may be denied. Submit reports this before starting remote work.
    }
    setRestored(true);
    return onSessionGenerationChanged(() => {
      try {
        sessionStorage.removeItem(referenceKey);
      } catch {
        /* Storage denied. */
      }
    });
  }, [user?.id, setAttempt]);

  const intent = useQuery({
    queryKey: key,
    enabled: restored && !!attempt && !attempt.submitting,
    queryFn: async ({ signal }) => {
      const result = attempt?.id
        ? await getDownloadIntent({ intent_id: attempt.id }, { signal })
        : await findDownloadIntent(
            { idempotency_key: attempt?.key ?? '' },
            { signal },
          );
      const current = queries.getQueryData<API.IntentResponse>(key);
      const latest =
        current && current.version > result.version ? current : result;
      return remember(latest);
    },
    refetchInterval: (query) =>
      query.state.error ||
      (query.state.data &&
        (terminal.has(query.state.data.status) ||
          Date.parse(query.state.data.deadline) <= Date.now()))
        ? false
        : 2_000,
    refetchOnWindowFocus: true,
    staleTime: 2_000,
  });
  const inspectionId = intent.data?.inspection_id;
  const inspection = useQuery({
    queryKey: privateQueryKey('inspection', inspectionId),
    enabled: !!inspectionId && intent.data?.status === 'ready',
    queryFn: ({ signal }) =>
      getInspection({ inspection_id: inspectionId ?? '' }, { signal }),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: true,
  });

  async function submit(input: string, reuse = false) {
    if (
      writing.current ||
      attempt?.submitting ||
      (attempt && !reuse && !terminal.has(intent.data?.status ?? 'queued'))
    )
      return;
    if (!user?.id) return;
    const requestKey = reuse && attempt?.key ? attempt.key : createUuid();
    // Persist only random references, before a request can be accepted. Raw
    // share text remains in the identity-owned in-memory draft.
    try {
      sessionStorage.setItem(
        referenceKey,
        JSON.stringify({ owner: user.id, key: requestKey }),
      );
    } catch {
      throw new ApiError(
        503,
        'intent_reference_unavailable',
        '无法保存恢复信息',
        '请允许此站点使用浏览器存储后重试，以便刷新后恢复任务。',
      );
    }
    writing.current = true;
    setOperationError(null);
    setAttempt({ key: requestKey, input, submitting: true });
    const queryKey = [...intentRoot, 'key', requestKey];
    try {
      await queries.cancelQueries({ queryKey });
      const result = await createDownloadIntent(
        { input },
        { headers: { 'Idempotency-Key': requestKey } },
      );
      queries.setQueryData(queryKey, remember(result));
    } catch (error) {
      // Definitive rejection means no new work was accepted. An uncertain
      // transport outcome keeps the key and is resolved by read-only lookup.
      if (
        error instanceof ApiError &&
        error.status >= 400 &&
        error.status < 500 &&
        error.status !== 408
      ) {
        if (!reuse) {
          setAttempt((current) =>
            current?.key === requestKey ? null : current,
          );
          sessionStorage.removeItem(referenceKey);
        }
        throw error;
      }
    } finally {
      writing.current = false;
      setAttempt((current) =>
        current?.key === requestKey
          ? { ...current, submitting: false }
          : current,
      );
    }
  }

  async function cancel() {
    if (!intent.data || cancelling) return;
    setCancelling(true);
    setOperationError(null);
    try {
      await queries.cancelQueries({
        queryKey: intentRoot,
      });
      const result = await cancelDownloadIntent({ intent_id: intent.data.id });
      queries.setQueryData(key, remember(result));
    } catch (error) {
      setOperationError(displayError(error));
    } finally {
      setCancelling(false);
    }
  }

  async function refresh() {
    if (
      !intent.data ||
      !attempt ||
      writing.current ||
      attempt.submitting ||
      cancelling
    )
      return;
    writing.current = true;
    setOperationError(null);
    const original = attempt;
    setAttempt({ ...original, submitting: true });
    let accepted = false;
    try {
      await queries.cancelQueries({ queryKey: intentRoot });
      const result = await refreshDownloadIntent({ intent_id: intent.data.id });
      queries.setQueryData(key, remember(result));
      accepted = true;
    } catch (error) {
      setOperationError(displayError(error));
    } finally {
      writing.current = false;
      setAttempt((current) =>
        current && current.key === original.key && current.id === original.id
          ? { ...current, submitting: false }
          : current,
      );
      // An uncertain write is resolved by a read, never an automatic POST.
      if (!accepted) void queries.invalidateQueries({ queryKey: key });
    }
  }

  function clear() {
    setAttempt(null);
    setOperationError(null);
    try {
      sessionStorage.removeItem(referenceKey);
    } catch {
      /* Already absent. */
    }
  }

  function resume(id: string) {
    if (
      !user?.id ||
      !uuid.test(id) ||
      writing.current ||
      attempt?.submitting ||
      cancelling
    )
      return false;
    // The server owns the task. Losing browser storage must not prevent this
    // read-only recovery; history remains available after the next sign-in.
    rememberDownloadIntent(user.id, id);
    setOperationError(null);
    setAttempt({ id, input: null, submitting: false });
    return true;
  }

  const missing =
    intent.error instanceof ApiError && intent.error.status === 404;
  const pending =
    !!attempt &&
    (attempt.submitting ||
      (!intent.data
        ? !(attempt.id && missing)
        : !terminal.has(intent.data.status)));
  const resultExpired =
    intent.data?.status === 'ready' &&
    ((inspection.data &&
      Date.parse(inspection.data.expires_at) <= Date.now()) ||
      (inspection.error instanceof ApiError &&
        inspection.error.code === 'resource_expired'));
  return {
    attempt,
    snapshot: intent.data,
    inspection:
      intent.data?.status === 'ready' && !attempt?.submitting
        ? inspection.data
        : undefined,
    resultExpired: !!resultExpired,
    pending,
    canResubmit:
      !attempt?.id &&
      !intent.data &&
      intent.error instanceof ApiError &&
      intent.error.status === 404,
    cancelling,
    restored,
    submit,
    cancel,
    refresh,
    clear,
    resume,
    error:
      operationError ??
      (intent.error
        ? intent.error instanceof ApiError && intent.error.status === 404
          ? attempt?.id
            ? '这条解析记录已不可用，可重新粘贴链接开始解析。'
            : '尚未确认接单，请查询原任务或使用同一请求重试。'
          : displayError(intent.error)
        : inspection.error
          ? displayError(inspection.error)
          : intent.data &&
              pending &&
              Date.parse(intent.data.deadline) <= Date.now()
            ? '等待时间已到，请查询后台任务的最终状态。'
            : null),
    retry: async () => {
      setOperationError(null);
      if (
        intent.error instanceof ApiError &&
        intent.error.status === 404 &&
        attempt?.input
      ) {
        try {
          await submit(attempt.input, true);
        } catch (error) {
          setOperationError(displayError(error));
        }
      } else {
        await intent.refetch();
        if (inspectionId && intent.data?.status === 'ready')
          await inspection.refetch();
      }
    },
  };
}
