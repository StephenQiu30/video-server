import { useMutation } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { type ProblemDetails, toProblem } from '@/utils/problem';
import { videoApi } from '@/utils/videoApi';
import {
  isExpired,
  type MediaFormat,
  type MediaSummary,
  parseJobId,
  parseMediaSummary,
} from '@/utils/videoData';

export type InspectState =
  | 'idle'
  | 'inspecting'
  | 'inspected'
  | 'inspect_failed'
  | 'expired';

export function useInspectFlow() {
  const [state, setState] = useState<InspectState>('idle');
  const [media, setMedia] = useState<MediaSummary | null>(null);
  const [selectedFormatId, setSelectedFormatId] = useState<string | null>(null);
  const [problem, setProblem] = useState<ProblemDetails | null>(null);
  const [createProblem, setCreateProblem] = useState<ProblemDetails | null>(
    null,
  );
  const [now, setNow] = useState(() => Date.now());
  const sequence = useRef(0);
  const inspectMutation = useMutation({
    mutationFn: videoApi.inspect,
    retry: false,
  });
  const createMutation = useMutation({
    mutationFn: videoApi.createDownload,
    retry: false,
  });

  useEffect(() => {
    if (state !== 'inspected') return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [state]);

  useEffect(() => {
    if (state === 'inspected' && media && isExpired(media.expiresAt, now)) {
      setState('expired');
      setCreateProblem(null);
    }
  }, [media, now, state]);

  const inspect = useCallback(
    async (url: string) => {
      const requestNumber = ++sequence.current;
      setState('inspecting');
      setMedia(null);
      setSelectedFormatId(null);
      setProblem(null);
      setCreateProblem(null);
      try {
        const result = parseMediaSummary(
          await inspectMutation.mutateAsync({ url }),
        );
        if (requestNumber !== sequence.current) return null;
        if (!result) throw new Error('INSPECT_RESPONSE_INVALID');
        setMedia(result);
        setSelectedFormatId(result.formats[0]?.id ?? null);
        setState(isExpired(result.expiresAt) ? 'expired' : 'inspected');
        return result;
      } catch (error) {
        if (requestNumber !== sequence.current) return null;
        setProblem(toProblem(error));
        setState('inspect_failed');
        return null;
      }
    },
    [inspectMutation],
  );

  const createDownload = useCallback(
    async (format: MediaFormat | null) => {
      if (
        !media ||
        !format ||
        state !== 'inspected' ||
        isExpired(media.expiresAt)
      )
        return null;
      if (createMutation.isPending) return null;
      setCreateProblem(null);
      const clientRequestId =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      try {
        const result = parseJobId(
          await createMutation.mutateAsync({
            source_id: media.id,
            format_id: format.id,
            client_request_id: clientRequestId,
          }),
        );
        if (!result) throw new Error('CREATE_RESPONSE_INVALID');
        return result;
      } catch (error) {
        setCreateProblem(toProblem(error));
        return null;
      }
    },
    [createMutation, media, state],
  );

  return {
    state,
    media,
    selectedFormatId,
    setSelectedFormatId,
    problem,
    createProblem,
    inspect,
    createDownload,
    isInspecting: state === 'inspecting' || inspectMutation.isPending,
    isCreating: createMutation.isPending,
  };
}
