import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { listDocuments } from '@/api/documents';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

export function useScreenplayDocuments(query: API.listDocumentsParams) {
  const params = { page: query.page, page_size: query.page_size };
  const result = useQuery({
    queryKey: privateQueryKey('documents', params),
    queryFn: ({ signal }) => listDocuments(params, { signal }),
    placeholderData: keepPreviousData,
  });
  return {
    data: result.data ?? null,
    error: result.error ? displayError(result.error) : null,
    loading: result.isPending,
    refreshing: result.isFetching,
    refresh: () => {
      void result.refetch();
    },
  };
}
