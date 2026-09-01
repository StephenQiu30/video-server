'use client';

import { ArrowClockwise, DownloadSimple, X } from '@phosphor-icons/react';

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
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';
import { localizedErrorMessage } from '@/lib/error-messages';
import type { DownloadJob } from '@/types/video';
import { DownloadExecutionSummary } from './download-execution-summary';
import {
  displayStage,
  statusDescription,
  statusHeading,
  statusLabels,
  statusVariant,
} from './download-state-model';

type Props = {
  action: 'cancel' | 'delete' | 'download' | 'retry' | null;
  job: DownloadJob;
  onCancel: () => void;
  onDownload: () => void;
  onRetry: () => void;
};

export default function DownloadState({
  action,
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
      <Badge variant={statusVariant(job.status)}>
        {statusLabels[job.status]}
      </Badge>
      <h2
        className="mt-4 text-2xl font-medium leading-tight tracking-[-0.035em] sm:text-[32px]"
        id="download-status-title"
      >
        {statusHeading(job)}
      </h2>
      <p className="mt-3 max-w-md text-sm leading-6 text-muted-foreground">
        {statusDescription(job)}
      </p>

      {!complete ? (
        <>
          <div className="mt-7 flex items-end justify-between gap-5">
            <span className="text-3xl font-medium leading-none tracking-[-0.045em] tabular-nums">
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
          <AlertTitle>文件已经不在存储中</AlertTitle>
          <AlertDescription>
            下载记录仍会保留。管理员清理文件后，你可以重新创建下载任务。
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="mt-7 grid gap-3">
        {complete && job.file_available ? (
          <Button
            className="w-full"
            disabled={action !== null}
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
            disabled={action !== null}
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
                disabled={action !== null}
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

      <DownloadExecutionSummary job={job} />
    </section>
  );
}
