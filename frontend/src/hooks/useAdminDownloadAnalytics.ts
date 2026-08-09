import { useEffect, useState } from 'react';

import {
  type AdminDownloadAnalytics,
  type AnalyticsPeriod,
  displayError,
  getAdminDownloadAnalytics,
} from '@/services/analytics';

export function useAdminDownloadAnalytics(days: AnalyticsPeriod) {
  const [data, setData] = useState<AdminDownloadAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let disposed = false;
    void retryKey;
    setData(null);
    setError(null);
    setLoading(true);

    getAdminDownloadAnalytics(days)
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
  }, [days, retryKey]);

  return {
    data,
    error,
    loading,
    retry: () => setRetryKey((current) => current + 1),
  };
}
