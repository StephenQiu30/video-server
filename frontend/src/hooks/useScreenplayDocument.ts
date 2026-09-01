import { useCallback, useEffect, useState } from 'react';

import { displayError, getScreenplayDocument } from '@/services/documents';
import type { ScreenplayDocument } from '@/types/video';

const activeStatuses = new Set(['uploading', 'verifying']);

export function useScreenplayDocument(
  documentId: string,
  pollIntervalMs = 3000,
) {
  const [document, setDocument] = useState<ScreenplayDocument | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cycle, setCycle] = useState(0);
  const visibleDocument = document?.id === documentId ? document : null;
  const status = visibleDocument?.status ?? null;
  const errorCode = visibleDocument?.error_code ?? null;
  const changingDocument = document !== null && visibleDocument === null;

  const load = useCallback(async () => {
    try {
      const result = await getScreenplayDocument(documentId);
      setDocument(result);
      setError(null);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    let disposed = false;
    void cycle;
    setLoading(true);
    setError(null);
    getScreenplayDocument(documentId)
      .then((result) => {
        if (!disposed) setDocument(result);
      })
      .catch((reason) => {
        if (!disposed) setError(displayError(reason));
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [cycle, documentId]);

  useEffect(() => {
    if (
      !status ||
      !activeStatuses.has(status) ||
      (status === 'uploading' && errorCode !== null)
    ) {
      return;
    }
    const timer = window.setInterval(() => void load(), pollIntervalMs);
    return () => window.clearInterval(timer);
  }, [errorCode, load, pollIntervalMs, status]);

  return {
    document: visibleDocument,
    error,
    loading: loading || changingDocument,
    refresh: () => setCycle((current) => current + 1),
  };
}
