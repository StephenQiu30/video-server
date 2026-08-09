'use client';

import {
  CheckCircle,
  DownloadSimple,
  ShieldCheck,
  SpinnerGap,
  X,
} from '@phosphor-icons/react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import type {
  DownloadJob,
  DownloadStage,
  DownloadStatus,
  MediaFormat,
} from '@/types/video';

type Props = {
  action: 'cancel' | 'download' | null;
  format?: MediaFormat;
  job: DownloadJob;
  onCancel: () => void;
  onDownload: () => void;
};

const statusLabels: Record<DownloadStatus, string> = {
  queued: '等待处理',
  running: '正在下载',
  retry_wait: '等待重试',
  succeeded: '下载已完成',
  failed: '下载失败',
  cancelled: '任务已取消',
};

const stageLabels: Record<DownloadStage, string> = {
  revalidating: '重新验证',
  downloading: '下载媒体',
  remuxing: '封装媒体',
  verifying: '校验文件',
  uploading: '保存制品',
};

export default function DownloadState({
  action,
  format,
  job,
  onCancel,
  onDownload,
}: Props) {
  const active = ['queued', 'running', 'retry_wait'].includes(job.status);
  const complete = job.status === 'succeeded';

  return (
    <section aria-labelledby="download-status-title" className="self-center">
      <div className="flex items-start justify-between gap-5">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">
            Download status
          </p>
          <h2
            className="mt-3 text-3xl font-semibold tracking-[-0.035em]"
            id="download-status-title"
          >
            {statusLabels[job.status]}
          </h2>
        </div>
        <Badge variant={complete ? 'success' : 'neutral'}>
          第 {job.attempt} 次尝试
        </Badge>
      </div>

      <dl className="mt-8 grid grid-cols-3 gap-4 border-y py-5 text-sm">
        <Meta
          label="格式"
          value={format?.plan.container_preference.toUpperCase() ?? '—'}
        />
        <Meta label="清晰度" value={format ? `${format.plan.height}P` : '—'} />
        <Meta label="阶段" value={displayStage(job)} />
      </dl>

      <div className="mt-7 flex items-end justify-between">
        <span className="font-mono text-4xl font-semibold tracking-[-0.05em]">
          {job.progress}%
        </span>
        <span className="text-sm text-muted-foreground">
          {statusLabels[job.status]}
        </span>
      </div>
      <Progress
        aria-label={`下载进度 ${job.progress}%`}
        className="mt-3"
        value={job.progress}
      />

      {job.status === 'failed' ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>下载失败</AlertTitle>
          <AlertDescription>
            {job.error_code ?? 'unknown_error'}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="mt-7 flex flex-wrap gap-3">
        {complete ? (
          <Button
            disabled={action === 'download'}
            onClick={onDownload}
            size="lg"
          >
            {action === 'download' ? (
              <SpinnerGap className="animate-spin" />
            ) : (
              <DownloadSimple />
            )}
            获取视频文件
          </Button>
        ) : null}
        {active ? (
          <Button
            disabled={action === 'cancel'}
            onClick={onCancel}
            size="lg"
            variant="outline"
          >
            {action === 'cancel' ? (
              <SpinnerGap className="animate-spin" />
            ) : (
              <X />
            )}
            取消任务
          </Button>
        ) : null}
      </div>

      <p className="mt-7 flex items-center gap-2 text-sm text-muted-foreground">
        {complete ? <ShieldCheck className="text-success" /> : <CheckCircle />}
        {complete ? '文件完整性验证通过' : '任务由隔离的媒体 Runner 执行'}
      </p>
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1.5 font-medium">{value}</dd>
    </div>
  );
}

function displayStage(job: DownloadJob): string {
  if (job.status === 'succeeded') return '已完成';
  if (job.status === 'failed') return '已失败';
  if (job.status === 'cancelled') return '已取消';
  return job.stage ? stageLabels[job.stage] : '等待调度';
}
