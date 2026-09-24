'use client';

import { ArrowClockwise } from '@phosphor-icons/react';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { deleteDocument as deleteScreenplayDocument } from '@/api/documents';
import { BackLink } from '@/components/layout/back-link';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { ScreenplayDocumentList } from '@/components/screenplay/screenplay-document-list';
import { ScreenplayUploadDialog } from '@/components/screenplay/screenplay-upload-dialog';
import { useScreenplayDocuments } from '@/components/screenplay/use-screenplay-documents';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

export default function ScreenplayDocumentsView() {
  const queries = useQueryClient();
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const state = useScreenplayDocuments({ page, page_size: 20 });

  async function remove(document: API.DocumentResponse) {
    setActionError(null);
    setPendingDeleteId(document.id);
    try {
      await deleteScreenplayDocument({
        document_id: encodeURIComponent(document.id),
      });
      queries.removeQueries({
        queryKey: privateQueryKey('document', document.id),
      });
      void queries.invalidateQueries({
        queryKey: privateQueryKey('documents'),
      });
      if (page > 1 && state.data?.items.length === 1) {
        setPage((current) => current - 1);
      }
    } catch (reason) {
      setActionError(displayError(reason));
    } finally {
      setPendingDeleteId(null);
    }
  }

  return (
    <div className="inner-page">
      <BackLink className="mb-4" fallbackHref="/" />
      <PageHeader
        action={
          <div className="flex flex-col gap-2 sm:flex-row">
            <ScreenplayUploadDialog />
            <Button
              className="bg-surface px-4"
              aria-busy={state.refreshing}
              disabled={state.refreshing}
              onClick={state.refresh}
              type="button"
              size="lg"
              variant="outline"
            >
              {state.refreshing ? (
                <Spinner aria-hidden data-icon="inline-start" />
              ) : (
                <ArrowClockwise aria-hidden data-icon="inline-start" />
              )}
              刷新
            </Button>
          </div>
        }
        description="核对导入状态、提取规模和规范化剧本文本。"
        title="剧本文档"
      />
      {state.error && !state.data ? (
        <PageErrorNotice
          className="mt-8"
          message={state.error}
          onRetry={state.refresh}
          retryLabel="重新加载"
          title="暂时无法读取剧本文档"
        />
      ) : null}
      {state.error && state.data ? (
        <FeedbackNotice
          action={
            <Button onClick={state.refresh} size="sm" variant="outline">
              重新加载
            </Button>
          }
          className="mt-8"
          description={state.error}
          title="剧本文档刷新失败"
          tone="error"
        />
      ) : null}
      {actionError ? (
        <FeedbackNotice
          className="mt-8"
          description={actionError}
          title="操作未完成"
          tone="error"
        />
      ) : null}
      <ScreenplayDocumentList
        data={state.data}
        loading={state.loading}
        onDelete={remove}
        pendingDeleteId={pendingDeleteId}
      />
      {state.data && state.data.total > state.data.page_size ? (
        <PagePagination
          ariaLabel="剧本文档分页"
          className="mt-10 justify-end"
          onPageChange={setPage}
          page={page}
          pages={Math.ceil(state.data.total / state.data.page_size)}
        />
      ) : null}
    </div>
  );
}
