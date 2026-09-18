import { useEffect, useState } from 'react';
import { getDownloadAnalytics as getAdminDownloadAnalytics } from '@/api/admin';
import { displayError } from '@/lib/request-error';

export function useAdminDownloadAnalytics(days: 7 | 30 | 90) {
  const [data, setData] = useState<API.DownloadAnalyticsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let disposed = false;
    void retryKey;
    setLoading(true);

    getAdminDownloadAnalytics({ days: days })
      .then((result) => {
        if (!disposed) {
          setData(result);
          setError(null);
        }
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
  }, [days, retryKey]);

  return {
    data,
    error,
    loading,
    retry: () => setRetryKey((current) => current + 1),
  };
}
