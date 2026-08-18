'use client';

import { ArrowClockwise } from '@phosphor-icons/react';
import { useMemo } from 'react';

import { BackLink } from '@/components/layout/back-link';
import ScreenplayAnalysisPanel from '@/components/screenplay/screenplay-analysis-panel';
import {
  documentStatusLabels,
  documentStatusVariant,
} from '@/components/screenplay/screenplay-document-format';
import { ScreenplayDocumentMetadata } from '@/components/screenplay/screenplay-document-metadata';
import { ScreenplayDocumentPreview } from '@/components/screenplay/screenplay-document-preview';
import {
  extractMarkdownHeadings,
  ScreenplayDocumentToc,
} from '@/components/screenplay/screenplay-document-toc';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useScreenplayDocument } from '@/hooks/useScreenplayDocument';

const metadataSkeletonKeys = [
  'format',
  'language',
  'scenes',
  'characters',
  'size',
  'status',
  'created',
  'expires',
] as const;

const tocSkeletonKeys = [
  'toc-1',
  'toc-2',
  'toc-3',
  'toc-4',
  'toc-5',
  'toc-6',
] as const;

const workspaceClassName =
  'mt-10 grid min-w-0 gap-10 lg:mt-12 lg:h-[clamp(34rem,72vh,56rem)] lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_280px] lg:grid-rows-[minmax(0,1fr)] lg:gap-0 lg:overflow-hidden';
const previewColumnClassName = 'min-w-0 lg:min-h-0 lg:overflow-hidden lg:pr-10';
const tocColumnClassName =
  'order-first min-w-0 lg:order-none lg:min-h-0 lg:overflow-hidden lg:border-l lg:pl-10';

export default function ScreenplayDocumentDetailView({
  documentId,
  pollIntervalMs,
}: {
  documentId: string;
  pollIntervalMs?: number;
}) {
  const state = useScreenplayDocument(documentId, pollIntervalMs);
  const headings = useMemo(
    () => extractMarkdownHeadings(state.document?.preview ?? ''),
    [state.document?.preview],
  );
  if (state.loading && !state.document) return <DocumentDetailSkeleton />;
  if (state.error && !state.document) {
    return <DocumentDetailError error={state.error} onRetry={state.refresh} />;
  }

  return (
    <div className="inner-page">
      <BackLink fallbackHref="/documents" />
      {state.error ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>无法读取剧本文档</AlertTitle>
          <AlertDescription className="flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
            <span>{state.error}</span>
            <Button onClick={state.refresh} size="sm" variant="outline">
              重试
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      {state.document ? (
        <>
          <header className="mt-7 flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between sm:gap-8">
            <div className="min-w-0">
              <Badge
                aria-live="polite"
                className="rounded-md px-2 py-1 font-normal"
                variant={documentStatusVariant(state.document.status)}
              >
                {documentStatusLabels[state.document.status]}
              </Badge>
              <h1 className="mt-4 break-words text-[clamp(2.25rem,4vw,3.75rem)] font-medium leading-[0.98] tracking-[-0.055em]">
                {state.document.title}
              </h1>
              <p className="mt-3 break-all text-sm text-muted-foreground">
                {state.document.original_filename}
              </p>
            </div>
            <Button
              className="h-11 w-full border-0 bg-surface px-4 sm:w-auto"
              disabled={state.loading}
              onClick={state.refresh}
              type="button"
              variant="outline"
            >
              <ArrowClockwise aria-hidden size={17} />
              刷新
            </Button>
          </header>
          <ScreenplayDocumentMetadata document={state.document} />
          <div
            className={workspaceClassName}
            data-testid="screenplay-document-workspace"
          >
            <div className={previewColumnClassName}>
              <ScreenplayDocumentPreview
                document={state.document}
                headings={headings}
              />
            </div>
            <div className={tocColumnClassName}>
              <ScreenplayDocumentToc headings={headings} />
            </div>
          </div>
          {state.document.status === 'ready' ? (
            <ScreenplayAnalysisPanel
              documentId={documentId}
              pollIntervalMs={pollIntervalMs}
            />
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function DocumentDetailSkeleton() {
  return (
    <div aria-busy className="inner-page">
      <span className="sr-only" role="status">
        正在读取剧本文档
      </span>
      <BackLink fallbackHref="/documents" />
      <div className="mt-8">
        <Skeleton className="h-7 w-24" />
        <Skeleton className="mt-4 h-12 w-2/5" />
        <Skeleton className="mt-3 h-4 w-1/3" />
      </div>
      <div className="mt-10 border-y border-border/70 py-5 sm:py-6">
        <Skeleton className="h-6 w-24" />
        <div className="mt-5 grid grid-cols-2 gap-5 sm:grid-cols-4 lg:grid-cols-8">
          {metadataSkeletonKeys.map((key) => (
            <div className="space-y-2" key={key}>
              <Skeleton className="h-3 w-14" />
              <Skeleton className="h-4 w-20" />
            </div>
          ))}
        </div>
      </div>
      <div className={workspaceClassName}>
        <div
          className={`${previewColumnClassName} flex flex-col space-y-4 lg:h-full`}
        >
          <div className="flex items-baseline justify-between gap-4">
            <Skeleton className="h-6 w-28" />
            <Skeleton className="h-4 w-20" />
          </div>
          <Skeleton className="min-h-0 w-full flex-1 rounded-none" />
        </div>
        <div className={`${tocColumnClassName} space-y-4`}>
          <Skeleton className="h-5 w-16" />
          <div className="space-y-3 pt-1">
            {tocSkeletonKeys.map((key) => (
              <Skeleton className="h-4 w-full" key={key} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function DocumentDetailError({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => void;
}) {
  return (
    <div className="inner-page">
      <BackLink fallbackHref="/documents" />
      <div className="mt-7 max-w-2xl">
        <h1 className="text-[36px] font-medium leading-[1.02] tracking-[-0.05em] sm:text-[52px]">
          无法读取剧本文档
        </h1>
        <p className="mt-4 text-sm text-muted-foreground">{error}</p>
        <Button className="mt-6" onClick={onRetry} type="button">
          重试
        </Button>
      </div>
    </div>
  );
}
