import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { getDownloadHistory } from '@/api/downloads';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

export function useDownloadHistory(query: API.getDownloadHistoryParams) {
  const params = {
    page: query.page,
    page_size: query.page_size,
    search: query.search,
    status: query.status,
  };
  const result = useQuery({
    queryKey: privateQueryKey('download-history', params),
    queryFn: ({ signal }) => getDownloadHistory(params, { signal }),
    placeholderData: keepPreviousData,
  });
  return {
    data: result.data ?? null,
    error: result.error ? displayError(result.error) : null,
    loading: result.isPending,
    refreshing: result.isFetching,
    retry: () => {
      void result.refetch();
    },
  };
}
