'use client';

import { useRouter } from 'next/navigation';
import AnalysisPanel from '@/components/analysis-panel';
import { BackLink } from '@/components/back-link';
import DownloadState from '@/components/download-state';
import MediaCover from '@/components/media-cover';
import { markNavigationPush } from '@/components/navigation-history';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { useDownloadJob } from '@/hooks/useDownloadJob';
import type { SemanticPlan } from '@/types/video';
import { formatDuration } from '@/utils/format';

export default function DownloadJobView({
  jobId,
  pollIntervalMs = 1500,
}: {
  jobId: string;
  pollIntervalMs?: number;
}) {
  const router = useRouter();
  const state = useDownloadJob(jobId, pollIntervalMs);
  const format = state.job?.format ?? undefined;
  const title = state.job?.title ?? '视频下载任务';
  const thumbnail = state.job?.thumbnail_url ?? null;
  const extractor = state.job?.extractor_key ?? null;
  const duration = state.job?.duration_seconds ?? undefined;

  async function retry() {
    const retried = await state.retry();
    if (!retried) return;
    const target = `/downloads/detail?jobId=${encodeURIComponent(retried.id)}`;
    markNavigationPush(target);
    router.push(target);
  }

  if (state.loading && !state.job) return <DownloadJobSkeleton />;

  return (
    <div className="inner-page">
      <BackLink fallbackHref="/history" />
      {state.error ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>无法读取下载任务</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}
      {state.job ? (
        <>
          <section className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.85fr)] lg:gap-0">
            <div className="min-w-0 lg:pr-12">
              <MediaCover
                alt={`${title}封面`}
                className="rounded-none ring-0"
                priority
                src={thumbnail}
              />
              <h1 className="mt-5 max-w-4xl text-[28px] font-medium leading-[1.12] tracking-[-0.035em] sm:text-[34px]">
                {title}
              </h1>
              <p className="mt-3 text-sm text-muted-foreground">
                {extractor ? `${extractor} · ` : ''}
                {formatLabel(format, duration)}
              </p>
            </div>
            <div className="min-w-0 lg:border-l lg:pl-12">
              <DownloadState
                action={state.action}
                format={format}
                job={state.job}
                onCancel={state.cancel}
                onDownload={state.download}
                onRetry={() => void retry()}
              />
              {!['succeeded', 'failed', 'cancelled'].includes(
                state.job.status,
              ) ? (
                <p
                  aria-live="polite"
                  className="mt-4 text-xs text-muted-foreground"
                >
                  {state.socketStatus === 'connected'
                    ? '实时状态已连接'
                    : state.socketStatus === 'degraded'
                      ? '实时连接中断，正在低频恢复'
                      : '正在连接实时状态'}
                </p>
              ) : null}
            </div>
          </section>
          {state.job.status === 'succeeded' ? (
            <AnalysisPanel downloadId={state.job.id} />
          ) : (
            <p className="mt-14 border-t py-8 text-sm text-muted-foreground sm:mt-16">
              下载并验证完成后，可继续生成视觉分镜、高光与资产目录。
            </p>
          )}
        </>
      ) : null}
    </div>
  );
}

function DownloadJobSkeleton() {
  return (
    <div className="inner-page">
      <BackLink fallbackHref="/history" />
      <div className="mt-9 grid gap-10 lg:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.85fr)] lg:gap-0">
        <div className="lg:pr-12">
          <Skeleton className="aspect-video rounded-none" />
          <Skeleton className="mt-6 h-9 w-3/4" />
          <Skeleton className="mt-3 h-4 w-1/2" />
        </div>
        <div className="lg:border-l lg:pl-12">
          <Skeleton className="h-80" />
        </div>
      </div>
    </div>
  );
}

function formatLabel(format?: SemanticPlan, duration?: number) {
  if (!format) return duration ? formatDuration(duration) : '正在读取媒体信息';
  return `${format.width}×${format.height} · ${format.video_codec_family.toUpperCase()} + ${format.audio_codec_family.toUpperCase()}${duration ? ` · ${formatDuration(duration)}` : ''}`;
}
