'use client';

import { ArrowLeftIcon } from '@phosphor-icons/react';
import Link from 'next/link';
import { useCallback, useState } from 'react';

import AnalysisPanel from '@/components/AnalysisPanel';
import DownloadState from '@/components/download-state';
import MediaCover from '@/components/media-cover';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { useDownloadJob } from '@/hooks/useDownloadJob';
import type { AnalysisJob, MediaFormat } from '@/types/video';
import { formatDuration } from '@/utils/format';

export default function DownloadJobView({
  jobId,
  pollIntervalMs = 1500,
}: {
  jobId: string;
  pollIntervalMs?: number;
}) {
  const state = useDownloadJob(jobId, pollIntervalMs);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const handleAnalysisJob = useCallback((job: AnalysisJob | null) => {
    setAnalysisJob(job);
  }, []);
  const format = state.inspection?.formats.find(
    (item) => item.id === state.job?.format_id,
  );

  if (state.loading && !state.job) return <DownloadSkeleton />;

  return (
    <main className="page-shell py-10">
      <Button asChild className="mb-8 -ml-2" variant="ghost">
        <Link href="/">
          <ArrowLeftIcon data-icon="inline-start" /> 返回新建下载
        </Link>
      </Button>
      {state.error ? (
        <Alert className="mb-7" variant="destructive">
          <AlertTitle>无法读取下载任务</AlertTitle>
          <AlertDescription>{state.error}</AlertDescription>
        </Alert>
      ) : null}
      {state.job ? (
        <>
          <section className="grid gap-10 lg:grid-cols-[minmax(0,1.08fr)_minmax(420px,0.92fr)]">
            <div className="lg:border-r lg:pr-10">
              <MediaCover
                alt={`${state.inspection?.title ?? '视频'} 视频封面`}
                duration={
                  state.inspection
                    ? formatDuration(state.inspection.duration_seconds)
                    : undefined
                }
                platform={state.inspection?.extractor_key}
                src={state.inspection?.thumbnail_url}
              />
              <h1 className="mt-7 text-balance text-3xl font-semibold tracking-tight">
                {state.inspection?.title ?? '视频下载任务'}
              </h1>
              <p className="mt-3 text-sm text-muted-foreground">
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
          {state.job.status === 'succeeded' ? (
            <AnalysisPanel
              downloadId={state.job.id}
              onJobChange={handleAnalysisJob}
            />
          ) : (
            <section className="mt-10 border-t py-10 text-muted-foreground">
              下载并验证完成后，可继续生成摘要与思维导图。
            </section>
          )}
          {analysisJob?.status === 'succeeded' ? (
            <span className="sr-only">分析已完成</span>
          ) : null}
        </>
      ) : null}
    </main>
  );
}

function DownloadSkeleton() {
  return (
    <main className="page-shell grid gap-10 py-24 lg:grid-cols-2">
      <Skeleton className="aspect-video w-full" />
      <div className="space-y-6">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-3 w-full" />
      </div>
    </main>
  );
}

function formatLabel(format?: MediaFormat, duration?: number) {
  if (!format) return duration ? formatDuration(duration) : '正在读取媒体信息';
  return `${format.plan.width}×${format.plan.height} · ${format.plan.video_codec_family.toUpperCase()} + ${format.plan.audio_codec_family.toUpperCase()} · ${duration ? formatDuration(duration) : ''}`;
}
