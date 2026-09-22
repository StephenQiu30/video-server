import { useQuery } from '@tanstack/react-query';
import { useCallback } from 'react';
import { listProviders } from '@/api/providers';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

export function useProviderStatuses() {
  const result = useQuery({
    queryKey: privateQueryKey('providers'),
    queryFn: ({ signal }) => listProviders({ signal }),
    staleTime: 15_000,
  });
  const { refetch } = result;
  const retry = useCallback(() => {
    void refetch();
  }, [refetch]);
  return {
    data: result.data ?? null,
    error: result.error ? displayError(result.error) : null,
    loading: result.isPending,
    refreshing: result.isFetching,
    retry,
  };
}
