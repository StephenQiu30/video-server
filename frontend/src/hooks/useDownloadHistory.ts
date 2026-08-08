import { useEffect, useState } from 'react';

import { displayError, getDownloadHistory } from '@/services/download';
import type { DownloadHistory, DownloadHistoryQuery } from '@/types/video';

export function useDownloadHistory(query: DownloadHistoryQuery) {
  const [data, setData] = useState<DownloadHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);
  const { page, page_size: pageSize, search, status } = query;

  useEffect(() => {
    let disposed = false;
    void retryKey;
    setLoading(true);
    setError(null);

    getDownloadHistory({ page, page_size: pageSize, search, status })
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
  }, [page, pageSize, status, search, retryKey]);

  return {
    data,
    error,
    loading,
    retry: () => setRetryKey((current) => current + 1),
  };
}
