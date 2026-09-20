import { useCallback, useEffect, useRef, useState } from 'react';
import { getDocumentImport as getScreenplayDocument } from '@/api/documents';
import { displayError } from '@/lib/request-error';

const activeStatuses = new Set(['uploading', 'verifying']);

export function useScreenplayDocument(
  documentId: string,
  pollIntervalMs = 3000,
) {
  const [document, setDocument] = useState<API.DocumentDetailResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cycle, setCycle] = useState(0);
  const requestId = useRef(0);
  const inFlightDocumentId = useRef<string | null>(null);
  const visibleDocument = document?.id === documentId ? document : null;
  const status = visibleDocument?.status ?? null;
  const errorCode = visibleDocument?.error_code ?? null;
  const changingDocument = document !== null && visibleDocument === null;

  const load = useCallback(async () => {
    if (inFlightDocumentId.current === documentId) return;
    inFlightDocumentId.current = documentId;
    const current = ++requestId.current;
    try {
      const result = await getScreenplayDocument({
        document_id: encodeURIComponent(documentId),
      });
      if (current === requestId.current) {
        setDocument(result);
        setError(null);
      }
    } catch (reason) {
      if (current === requestId.current) setError(displayError(reason));
    } finally {
      if (current === requestId.current) setLoading(false);
      if (inFlightDocumentId.current === documentId) {
        inFlightDocumentId.current = null;
      }
    }
  }, [documentId]);

  useEffect(() => {
    void cycle;
    setLoading(true);
    setError(null);
    void load();
    return () => {
      requestId.current += 1;
    };
  }, [cycle, load]);

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
