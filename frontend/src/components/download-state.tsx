import {
  CheckCircleIcon,
  DownloadSimpleIcon,
  ShieldCheckIcon,
  XIcon,
} from '@phosphor-icons/react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import type { DownloadJob, MediaFormat } from '@/types/video';

type DownloadStateProps = {
  action: 'cancel' | 'download' | null;
  format?: MediaFormat;
  job: DownloadJob;
  onCancel: () => void;
  onDownload: () => void;
};

export default function DownloadState({
  action,
  format,
  job,
  onCancel,
  onDownload,
}: DownloadStateProps) {
  const active = ['queued', 'running', 'retry_wait'].includes(job.status);
  const complete = job.status === 'succeeded';
  return (
    <section className="flex flex-col justify-center py-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs tracking-[0.18em] text-muted-foreground uppercase">
            Download status
          </p>
          <h2 className="mt-2 text-2xl font-semibold">
            {statusLabels[job.status]}
          </h2>
        </div>
        <Badge variant={complete ? 'secondary' : 'outline'}>
          第 {job.attempt} 次尝试
        </Badge>
      </div>
      <dl className="mt-8 grid grid-cols-3 border-y py-5 text-sm">
        <Meta
          label="格式"
          value={format?.plan.container_preference.toUpperCase() ?? '—'}
        />
        <Meta label="清晰度" value={format ? `${format.plan.height}P` : '—'} />
        <Meta label="阶段" value={displayStage(job)} />
      </dl>
      <div className="mt-8">
        <div className="mb-3 flex items-end justify-between">
          <span className="font-mono text-4xl tracking-tight text-brand">
            {job.progress}%
          </span>
          <span className="text-sm text-muted-foreground">
            {statusLabels[job.status]}
          </span>
        </div>
        <Progress value={job.progress} />
      </div>
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
            className="h-11 flex-1"
            disabled={action === 'download'}
            onClick={onDownload}
          >
            <DownloadSimpleIcon data-icon="inline-start" /> 获取视频文件
          </Button>
        ) : null}
        {active ? (
          <Button
            disabled={action === 'cancel'}
            onClick={onCancel}
            variant="outline"
          >
            <XIcon data-icon="inline-start" /> 取消任务
          </Button>
        ) : null}
      </div>
      <p className="mt-6 flex items-center gap-2 text-xs text-muted-foreground">
        {complete ? <ShieldCheckIcon /> : <CheckCircleIcon />}
        {complete ? '文件完整性验证通过' : '任务由隔离的媒体 Runner 执行'}
      </p>
    </section>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}

const statusLabels = {
  queued: '等待处理',
  running: '正在下载',
  retry_wait: '等待重试',
  succeeded: '下载已完成',
  failed: '下载失败',
  cancelled: '任务已取消',
};

const stageLabels = {
  queued: '等待调度',
  revalidating: '重新验证',
  downloading: '下载媒体',
  remuxing: '封装媒体',
  verifying: '校验文件',
  uploading: '保存制品',
};

function displayStage(job: DownloadJob): string {
  if (job.status === 'succeeded') return '已完成';
  if (job.status === 'failed') return '已失败';
  if (job.status === 'cancelled') return '已取消';
  return stageLabels[job.stage ?? 'queued'];
}
