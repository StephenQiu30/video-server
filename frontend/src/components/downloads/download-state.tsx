'use client';

import {
  ArrowClockwise,
  CheckCircle,
  DownloadSimple,
  ShieldCheck,
  X,
} from '@phosphor-icons/react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Spinner } from '@/components/ui/spinner';
import { localizedErrorMessage } from '@/lib/error-messages';
import type {
  DownloadJob,
  DownloadStage,
  DownloadStatus,
  SemanticPlan,
} from '@/types/video';

type Props = {
  action: 'cancel' | 'download' | 'retry' | null;
  format?: SemanticPlan;
  job: DownloadJob;
  onCancel: () => void;
  onDownload: () => void;
  onRetry: () => void;
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
  onRetry,
}: Props) {
  const active = ['queued', 'running', 'retry_wait'].includes(job.status);
  const complete = job.status === 'succeeded';
  const retryable =
    ['failed', 'cancelled'].includes(job.status) ||
    (complete && !job.file_available);

  return (
    <section aria-labelledby="download-status-title" className="self-start">
      <p className="text-sm font-medium">任务状态</p>
      <h2
        className="mt-5 text-[32px] font-medium leading-none tracking-[-0.045em] sm:text-[38px]"
        id="download-status-title"
      >
        {statusLabels[job.status]}
      </h2>

      <Separator className="mt-8" />
      <dl className="grid grid-cols-2 gap-x-6 gap-y-6 py-6 text-sm">
        <Meta
          label="格式"
          value={format?.container_preference.toUpperCase() ?? '—'}
        />
        <Meta
          label="分辨率"
          value={format ? `${format.width}×${format.height}` : '—'}
        />
        {complete ? (
          <Meta
            label="文件存储"
            value={job.file_available ? '持久保存' : '已清理'}
          />
        ) : (
          <Meta label="当前阶段" value={displayStage(job)} />
        )}
        <Meta label="执行尝试" value={`第 ${job.attempt} 次`} />
      </dl>
      <Separator />

      {!complete ? (
        <>
          <div className="mt-8 flex items-end justify-between gap-5">
            <span className="text-[42px] font-medium leading-none tracking-[-0.06em] tabular-nums">
              {job.progress}%
            </span>
            <span className="text-sm text-muted-foreground">
              {displayStage(job)}
            </span>
          </div>
          <Progress
            aria-label={`下载进度 ${job.progress}%`}
            className="mt-3"
            value={job.progress}
          />
        </>
      ) : null}

      {job.status === 'failed' ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>下载失败</AlertTitle>
          <AlertDescription>
            {localizedErrorMessage(job.error_code) ??
              '下载任务未能完成，请稍后重试。'}
          </AlertDescription>
        </Alert>
      ) : null}

      {complete && !job.file_available ? (
        <Alert className="mt-6" variant="warning">
          <AlertTitle>视频文件已清理</AlertTitle>
          <AlertDescription>
            下载记录仍会保留。管理员清理文件后，你可以重新创建下载任务。
          </AlertDescription>
        </Alert>
      ) : null}

      <div className={complete ? 'mt-7 grid gap-3' : 'mt-8 grid gap-3'}>
        {complete && job.file_available ? (
          <Button
            className="w-full"
            disabled={action === 'download'}
            onClick={onDownload}
            size="lg"
          >
            {action === 'download' ? (
              <Spinner aria-hidden />
            ) : (
              <DownloadSimple />
            )}
            获取视频文件
          </Button>
        ) : null}
        {retryable ? (
          <Button
            className="w-full"
            disabled={action === 'retry'}
            onClick={onRetry}
            size="lg"
          >
            {action === 'retry' ? <Spinner aria-hidden /> : <ArrowClockwise />}
            重新下载
          </Button>
        ) : null}
        {active ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                className="w-full"
                disabled={action === 'cancel'}
                size="lg"
                variant="outline"
              >
                {action === 'cancel' ? <Spinner aria-hidden /> : <X />}
                取消任务
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent size="sm">
              <AlertDialogHeader>
                <AlertDialogMedia>
                  <X aria-hidden />
                </AlertDialogMedia>
                <AlertDialogTitle>取消当前下载任务？</AlertDialogTitle>
                <AlertDialogDescription>
                  确认后将停止当前下载。取消后可在当前页面重新下载。
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>继续下载</AlertDialogCancel>
                <AlertDialogAction variant="destructive" onClick={onCancel}>
                  确认取消下载
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : null}
      </div>

      <p className="mt-8 flex items-center gap-2 text-sm text-muted-foreground">
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
      <dd className="mt-2 font-medium">{value}</dd>
    </div>
  );
}

function displayStage(job: DownloadJob): string {
  if (job.status === 'succeeded') return '已完成';
  if (job.status === 'failed') return '已失败';
  if (job.status === 'cancelled') return '已取消';
  return job.stage ? stageLabels[job.stage] : '等待调度';
}
