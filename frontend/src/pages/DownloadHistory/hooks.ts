import { useEffect, useState } from 'react';

import { displayError, getDownloadHistory } from '@/services/download';
import type { DownloadHistory, DownloadHistoryQuery } from '@/types/video';

export function useDownloadHistory(query: DownloadHistoryQuery) {
  const [data, setData] = useState<DownloadHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);

  // biome-ignore lint/correctness/useExhaustiveDependencies: query is the request identity.
  useEffect(() => {
    let disposed = false;
    setLoading(true);
    setError(null);

    getDownloadHistory(query)
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
  }, [query.page, query.page_size, query.status, query.search, retryKey]);

  return {
    data,
    error,
    loading,
    retry: () => setRetryKey((current) => current + 1),
  };
}
