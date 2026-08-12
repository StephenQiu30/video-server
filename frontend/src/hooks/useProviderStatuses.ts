import { useEffect, useState } from 'react';

import {
  displayError,
  listProviders,
  type ProviderStatusList,
} from '@/services/providers';

export function useProviderStatuses() {
  const [data, setData] = useState<ProviderStatusList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let disposed = false;
    void retryKey;
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

  return {
    data,
    error,
    loading,
    retry: () => setRetryKey((current) => current + 1),
  };
}
