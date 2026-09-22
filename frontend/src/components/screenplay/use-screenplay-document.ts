import { useQuery } from '@tanstack/react-query';
import { getDocumentImport } from '@/api/documents';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

export function useScreenplayDocument(
  documentId: string,
  pollIntervalMs = 3000,
) {
  const result = useQuery({
    queryKey: privateQueryKey('document', documentId),
    queryFn: ({ signal }) =>
      getDocumentImport(
        { document_id: encodeURIComponent(documentId) },
        { signal },
      ),
    refetchInterval: (query) => {
      const item = query.state.data;
      return item &&
        (item.status === 'verifying' ||
          (item.status === 'uploading' && !item.error_code))
        ? pollIntervalMs
        : false;
    },
    refetchIntervalInBackground: false,
  });
  return {
    document: result.data ?? null,
    error: result.error ? displayError(result.error) : null,
    loading: result.isPending,
    refresh: () => {
      void result.refetch();
    },
  };
}
