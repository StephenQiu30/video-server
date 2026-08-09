'use client';

import { ArrowLeft } from '@phosphor-icons/react';
import Link from 'next/link';

import AnalysisPanel from '@/components/analysis-panel';
import DownloadState from '@/components/download-state';
import MediaCover from '@/components/media-cover';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useDownloadJob } from '@/hooks/useDownloadJob';
import type { MediaFormat } from '@/types/video';
import { formatDuration } from '@/utils/format';

export default function DownloadJobView({
  jobId,
  pollIntervalMs = 1500,
}: {
  jobId: string;
  pollIntervalMs?: number;
}) {
  const state = useDownloadJob(jobId, pollIntervalMs);
  const format = state.inspection?.formats.find(
    (item) => item.id === state.job?.format_id,
  );

  if (state.loading && !state.job) return <DownloadJobSkeleton />;

  return (
    <main className="content-shell py-10 sm:py-14">
      <Button asChild className="-ml-3" variant="ghost">
        <Link href="/">
          <ArrowLeft aria-hidden size={17} />
          返回新建下载
        </Link>
      </Button>
      {state.error ? (
        <Alert className="mt-7" variant="destructive">
          <AlertTitle>无法读取下载任务</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}
      {state.job ? (
        <>
          <section className="mt-8 grid gap-10 border-y py-9 lg:grid-cols-[minmax(0,0.9fr)_minmax(380px,1.1fr)] lg:gap-14">
            <div>
              <MediaCover
                alt={`${state.inspection?.title ?? '视频'}封面`}
                duration={
                  state.inspection
                    ? formatDuration(state.inspection.duration_seconds)
                    : undefined
                }
                platform={state.inspection?.extractor_key}
                priority
                src={state.inspection?.thumbnail_url}
              />
              <h1 className="mt-6 text-2xl font-semibold tracking-[-0.025em]">
                {state.inspection?.title ?? '视频下载任务'}
              </h1>
              <p className="mt-2 text-sm text-muted-foreground">
                {formatLabel(format, state.inspection?.duration_seconds)}
              </p>
            </div>
            <DownloadState
              action={state.action}
              format={format}
              job={state.job}
              onCancel={state.cancel}
              onDownload={state.download}
            />
          </section>
          {state.inspectionError ? (
            <p className="mt-4 text-sm text-warning">{state.inspectionError}</p>
          ) : null}
          {state.job.status === 'succeeded' ? (
            <AnalysisPanel downloadId={state.job.id} />
          ) : (
            <p className="border-b py-8 text-sm text-muted-foreground">
              下载并验证完成后，可继续生成摘要与思维导图。
            </p>
          )}
        </>
      ) : null}
    </main>
  );
}

function DownloadJobSkeleton() {
  return (
    <main className="content-shell grid gap-10 py-16 lg:grid-cols-2">
      <Skeleton className="aspect-video" />
      <Skeleton className="h-80" />
    </main>
  );
}

function formatLabel(format?: MediaFormat, duration?: number) {
  if (!format) return duration ? formatDuration(duration) : '正在读取媒体信息';
  return `${format.plan.width}×${format.plan.height} · ${format.plan.video_codec_family.toUpperCase()} + ${format.plan.audio_codec_family.toUpperCase()}${duration ? ` · ${formatDuration(duration)}` : ''}`;
}
