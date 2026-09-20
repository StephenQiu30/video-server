import { useCallback, useEffect, useState } from 'react';
import { listProviders } from '@/api/providers';
import { displayError } from '@/lib/request-error';

export function useProviderStatuses() {
  const [data, setData] = useState<API.ProviderListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let disposed = false;
    void retryKey;
    setError(null);
    setLoading(true);

    listProviders()
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
  }, [retryKey]);

  const retry = useCallback(() => {
    setError(null);
    setRetryKey((current) => current + 1);
  }, []);

  return {
    data,
    error,
    loading,
    retry,
  };
}
