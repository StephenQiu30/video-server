'use client';

import { ArrowClockwise } from '@phosphor-icons/react';
import { useState } from 'react';

import { BackLink } from '@/components/layout/back-link';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { ScreenplayDocumentList } from '@/components/screenplay/screenplay-document-list';
import { ScreenplayUploadDialog } from '@/components/screenplay/screenplay-upload-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useScreenplayDocuments } from '@/hooks/useScreenplayDocuments';
import { deleteScreenplayDocument, displayError } from '@/services/documents';
import type { ScreenplayDocumentSummary } from '@/types/video';

export default function ScreenplayDocumentsView() {
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const state = useScreenplayDocuments({ page, page_size: 20 });

  async function remove(document: ScreenplayDocumentSummary) {
    setActionError(null);
    setPendingDeleteId(document.id);
    try {
      await deleteScreenplayDocument(document.id);
      if (page > 1 && state.data?.items.length === 1) {
        setPage((current) => current - 1);
      } else {
        state.refresh();
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
              className="h-11 border-0 bg-surface px-4"
              disabled={state.loading}
              onClick={state.refresh}
              type="button"
              variant="outline"
            >
              <ArrowClockwise aria-hidden size={17} />
              刷新
            </Button>
          </div>
        }
        description="核对导入状态、提取规模和规范化剧本文本。"
        title="剧本文档"
      />
      {state.error || actionError ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription>{state.error ?? actionError}</AlertDescription>
        </Alert>
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
