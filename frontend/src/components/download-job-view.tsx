'use client';

import AnalysisPanel from '@/components/analysis-panel';
import { BackLink } from '@/components/back-link';
import DownloadState from '@/components/download-state';
import MediaCover from '@/components/media-cover';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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
    <main className="content-shell py-10 sm:py-14 lg:py-16">
      <BackLink fallbackHref="/history" />
      <p className="eyebrow mt-7 text-muted-foreground">02 / 下载任务</p>
      {state.error ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>无法读取下载任务</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}
      {state.job ? (
        <>
          <section className="mt-9 grid gap-10 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)] lg:gap-0">
            <div className="min-w-0 lg:pr-12">
              <MediaCover
                alt={`${state.inspection?.title ?? '视频'}封面`}
                className="rounded-none ring-0"
                priority
                src={state.inspection?.thumbnail_url}
              />
              <h1 className="mt-6 max-w-4xl text-[28px] font-medium leading-[1.12] tracking-[-0.035em] sm:text-[36px]">
                {state.inspection?.title ?? '视频下载任务'}
              </h1>
              <p className="mt-3 text-sm text-muted-foreground">
                {state.inspection?.extractor_key
                  ? `${state.inspection.extractor_key} · `
                  : ''}
                {formatLabel(format, state.inspection?.duration_seconds)}
              </p>
            </div>
            <div className="min-w-0 lg:border-l lg:pl-12">
              <DownloadState
                action={state.action}
                format={format}
                job={state.job}
                onCancel={state.cancel}
                onDownload={state.download}
              />
            </div>
          </section>
          {state.inspectionError ? (
            <p className="mt-6 text-sm text-warning">{state.inspectionError}</p>
          ) : null}
          {state.job.status === 'succeeded' ? (
            <AnalysisPanel downloadId={state.job.id} />
          ) : (
            <p className="mt-14 border-t py-8 text-sm text-muted-foreground sm:mt-16">
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
    <main className="content-shell py-10 sm:py-14 lg:py-16">
      <BackLink fallbackHref="/history" />
      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)] lg:gap-0">
        <div className="lg:pr-12">
          <Skeleton className="aspect-video rounded-none" />
          <Skeleton className="mt-6 h-9 w-3/4" />
          <Skeleton className="mt-3 h-4 w-1/2" />
        </div>
        <div className="lg:border-l lg:pl-12">
          <Skeleton className="h-80" />
        </div>
      </div>
    </main>
  );
}

function formatLabel(format?: MediaFormat, duration?: number) {
  if (!format) return duration ? formatDuration(duration) : '正在读取媒体信息';
  return `${format.plan.width}×${format.plan.height} · ${format.plan.video_codec_family.toUpperCase()} + ${format.plan.audio_codec_family.toUpperCase()}${duration ? ` · ${formatDuration(duration)}` : ''}`;
}
