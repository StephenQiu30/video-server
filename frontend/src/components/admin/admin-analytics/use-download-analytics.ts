import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getDownloadAnalytics } from '@/api/admin';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

export function useAdminDownloadAnalytics(days: 7 | 30 | 90) {
  const result = useQuery({
    queryKey: privateQueryKey('admin-download-analytics', days),
    queryFn: ({ signal }) => getDownloadAnalytics({ days }, { signal }),
    placeholderData: keepPreviousData,
  });
  return {
    data: result.data ?? null,
    error: result.error ? displayError(result.error) : null,
    loading: result.isFetching,
    retry: () => {
      void result.refetch();
    },
  };
}
