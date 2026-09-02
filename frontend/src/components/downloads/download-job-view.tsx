'use client';

import { useRouter } from 'next/navigation';
import AnalysisPanel from '@/components/analysis/analysis-panel';
import { DownloadDeleteDialog } from '@/components/downloads/download-delete-dialog';
import DownloadState from '@/components/downloads/download-state';
import DownloadVideoPreview from '@/components/downloads/download-video-preview';
import MediaCover from '@/components/intake/media-cover';
import { BackLink } from '@/components/layout/back-link';
import { markNavigationPush } from '@/components/layout/navigation-history';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { useDownloadJob } from '@/hooks/useDownloadJob';
import type { MediaKind, SemanticPlan } from '@/types/video';
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
  const gallery = state.job?.media_kind === 'image_gallery';
  const collection = state.job?.media_kind === 'video_collection';
  const title = state.job?.title ?? state.job?.source_label ?? '媒体下载任务';
  const thumbnail = state.job?.thumbnail_url ?? null;
  const extractor = state.job?.extractor_key ?? null;
  const sourceLabel = state.job?.source_label ?? null;
  const duration = state.job?.duration_seconds ?? undefined;

  async function retry() {
    const retried = await state.retry();
    if (!retried) return;
    const target = `/downloads/detail?jobId=${encodeURIComponent(retried.id)}`;
    markNavigationPush(target);
    router.push(target);
  }

  async function remove() {
    if (!(await state.remove())) return;
    router.replace('/history');
  }

  if (state.loading && !state.job) return <DownloadJobSkeleton />;

  return (
    <div className="inner-page">
      <div className="flex items-center justify-between gap-4">
        <BackLink fallbackHref="/history" />
        {state.job ? (
          <DownloadDeleteDialog
            active={
              !['succeeded', 'failed', 'cancelled'].includes(state.job.status)
            }
            busy={state.action !== null}
            onDelete={remove}
          />
        ) : null}
      </div>
      {state.error ? (
        <Alert className="mt-8" variant="destructive">
          <AlertTitle>{errorTitle(state.errorKind)}</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}
      {state.job ? (
        <>
          <header className="mt-8 max-w-5xl">
            <h1 className="text-[34px] font-medium leading-[1.06] tracking-[-0.045em] sm:text-[42px] lg:text-[48px]">
              {title}
            </h1>
            <p className="mt-4 text-sm text-muted-foreground">
              {sourceLabel ? `${sourceLabel} · ` : ''}
              {extractor && extractor !== sourceLabel ? `${extractor} · ` : ''}
              {formatLabel(
                format,
                duration,
                state.job?.media_kind,
                state.job?.asset_count,
              )}
            </p>
          </header>
          <section className="mt-8 grid items-start gap-10 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.65fr)] lg:gap-16 xl:gap-24">
            <div className="min-w-0">
              {state.job.status === 'succeeded' &&
              state.job.file_available &&
              !gallery && !collection ? (
                <DownloadVideoPreview
                  container={
                    format?.container_preference === 'mp4' ||
                    format?.container_preference === 'webm'
                      ? format.container_preference
                      : undefined
                  }
                  downloadId={state.job.id}
                  poster={thumbnail}
                  title={title}
                />
              ) : (
                <MediaCover
                  alt={`${title}媒体封面`}
                  className="rounded-none ring-0"
                  pending={
                    !['succeeded', 'failed', 'cancelled'].includes(
                      state.job.status,
                    )
                  }
                  priority
                  src={thumbnail}
                />
              )}
            </div>
            <div className="min-w-0 lg:pt-1">
              <DownloadState
                action={state.action}
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
            !gallery && !collection ? (
              <div className="mt-14 sm:mt-20">
                <AnalysisPanel downloadId={state.job.id} />
              </div>
            ) : null
          ) : ['failed', 'cancelled'].includes(state.job.status) ? null : (
            <p className="mt-14 py-8 text-sm text-muted-foreground sm:mt-20">
              下载并验证完成后，可继续生成视觉分镜、高光与资产目录。
            </p>
          )}
        </>
      ) : null}
    </div>
  );
}

function errorTitle(kind: 'load' | 'sync' | 'action' | null) {
  if (kind === 'load') return '无法读取下载任务';
  if (kind === 'sync') return '状态同步暂时中断';
  if (kind === 'action') return '操作未完成';
  return '请求未完成';
}

function DownloadJobSkeleton() {
  return (
    <div className="inner-page">
      <BackLink fallbackHref="/history" />
      <div className="mt-9 max-w-5xl">
        <Skeleton className="h-11 w-3/4" />
        <Skeleton className="mt-4 h-4 w-1/2" />
      </div>
      <div className="mt-8 grid items-start gap-10 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.65fr)] lg:gap-16 xl:gap-24">
        <div>
          <Skeleton className="aspect-video rounded-none" />
        </div>
        <div className="lg:pt-1">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="mt-5 h-9 w-4/5" />
          <Skeleton className="mt-4 h-5 w-full" />
          <Skeleton className="mt-8 h-11 w-full" />
          <Skeleton className="mt-7 h-11 w-3/4" />
        </div>
      </div>
    </div>
  );
}

function formatLabel(
  format: SemanticPlan | null | undefined,
  duration: number | undefined,
  mediaKind: MediaKind | undefined,
  assetCount: number | undefined,
) {
  if (mediaKind === 'image_gallery') {
    return `${assetCount ?? 0} 张原图 · ZIP`;
  }
  if (mediaKind === 'video_collection') {
    return `${assetCount ?? 0} 个视频 · ZIP`;
  }
  if (!format) return duration ? formatDuration(duration) : '正在读取媒体信息';
  return `${format.width}×${format.height} · ${format.video_codec_family.toUpperCase()} + ${format.audio_codec_family.toUpperCase()}${duration ? ` · ${formatDuration(duration)}` : ''}`;
}
