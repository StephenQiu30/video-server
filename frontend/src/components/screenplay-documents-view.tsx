'use client';

import { ArrowClockwise } from '@phosphor-icons/react';
import { useState } from 'react';

import { BackLink } from '@/components/back-link';
import { PageHeader } from '@/components/page-header';
import { PagePagination } from '@/components/page-pagination';
import { ScreenplayDocumentList } from '@/components/screenplay-document-list';
import { ScreenplayUploadDialog } from '@/components/screenplay-upload-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useScreenplayDocuments } from '@/hooks/useScreenplayDocuments';

export default function ScreenplayDocumentsView() {
  const [page, setPage] = useState(1);
  const state = useScreenplayDocuments({ page, page_size: 20 });

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
      {state.error ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>无法读取剧本文档</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}
      <ScreenplayDocumentList data={state.data} loading={state.loading} />
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
