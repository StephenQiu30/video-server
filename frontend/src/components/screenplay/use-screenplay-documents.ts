import { useEffect, useState } from 'react';
import { listDocuments as listScreenplayDocuments } from '@/api/documents';
import { displayError } from '@/lib/request-error';

export function useScreenplayDocuments(query: API.listDocumentsParams) {
  const [data, setData] = useState<API.DocumentPageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [cycle, setCycle] = useState(0);
  const { page, page_size: pageSize } = query;

  useEffect(() => {
    let disposed = false;
    void cycle;
    setLoading(true);
    setError(null);
    listScreenplayDocuments({ page, page_size: pageSize })
      .then((result) => {
        if (!disposed) setData(result);
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
  }, [cycle, page, pageSize]);

  return {
    data,
    error,
    loading,
    refresh: () => setCycle((current) => current + 1),
  };
}
