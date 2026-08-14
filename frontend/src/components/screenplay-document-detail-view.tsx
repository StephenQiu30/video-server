'use client';

import { ArrowClockwise } from '@phosphor-icons/react';

import { BackLink } from '@/components/back-link';
import {
  documentStatusLabels,
  documentStatusVariant,
} from '@/components/screenplay-document-format';
import { ScreenplayDocumentMetadata } from '@/components/screenplay-document-metadata';
import { ScreenplayDocumentPreview } from '@/components/screenplay-document-preview';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useScreenplayDocument } from '@/hooks/useScreenplayDocument';

export default function ScreenplayDocumentDetailView({
  documentId,
  pollIntervalMs,
}: {
  documentId: string;
  pollIntervalMs?: number;
}) {
  const state = useScreenplayDocument(documentId, pollIntervalMs);
  if (state.loading && !state.document) return <DocumentDetailSkeleton />;
  if (state.error && !state.document) {
    return <DocumentDetailError error={state.error} onRetry={state.refresh} />;
  }

  return (
    <main className="content-shell inner-page">
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
          <div className="mt-10 grid min-w-0 gap-12 lg:mt-14 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-0">
            <div className="min-w-0 lg:pr-12">
              <ScreenplayDocumentPreview document={state.document} />
            </div>
            <div className="min-w-0 lg:border-l lg:pl-12">
              <ScreenplayDocumentMetadata document={state.document} />
            </div>
          </div>
        </>
      ) : null}
    </main>
  );
}

function DocumentDetailSkeleton() {
  return (
    <main aria-busy className="content-shell inner-page">
      <span className="sr-only" role="status">
        正在读取剧本文档
      </span>
      <BackLink fallbackHref="/documents" />
      <div className="mt-8">
        <Skeleton className="h-7 w-24" />
        <Skeleton className="mt-4 h-12 w-2/5" />
        <Skeleton className="mt-3 h-4 w-1/3" />
      </div>
      <div className="mt-12 grid gap-12 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-0">
        <div className="lg:pr-12">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="mt-4 h-[28rem] w-full rounded-none" />
        </div>
        <div className="lg:border-l lg:pl-12">
          <Skeleton className="h-6 w-24" />
          <Skeleton className="mt-4 h-80 w-full rounded-none" />
        </div>
      </div>
    </main>
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
    <main className="content-shell inner-page">
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
    </main>
  );
}
