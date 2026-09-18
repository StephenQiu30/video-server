import { useEffect, useState } from 'react';
import { getDownloadHistory } from '@/api/downloads';
import { displayError } from '@/lib/request-error';
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
  }, [page, pageSize, retryKey, search, status]);

  return {
    data,
    error,
    loading,
    retry: () => setRetryKey((current) => current + 1),
  };
}
