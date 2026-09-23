'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import type { RefObject } from 'react';
import { getDownloadIntent } from '@/api/downloadIntents';
import { getDownload } from '@/api/downloads';
import {
  displayStage,
  failureDescription,
  statusDescription,
  statusHeading,
  statusLabels,
  statusVariant,
} from '@/components/downloads/download-state-model';
import {
  intentStatusVariant,
  intentTitle,
} from '@/components/intake/intent-status';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import MediaCover from '@/components/media/media-cover';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { localizedErrorMessage } from '@/lib/error-messages';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

const activeIntentStatuses = new Set<API.IntentStatus>([
  'queued',
  'preparing',
  'resolving',
  'retry_wait',
]);
const activeDownloadStatuses = new Set<API.DownloadStatus>([
  'queued',
  'running',
  'retry_wait',
]);

export function IntentHistoryDialog({
  item,
  onClose,
  triggerRef,
}: {
  item: API.IntentHistoryItemResponse | null;
  onClose: () => void;
  triggerRef: RefObject<HTMLButtonElement | null>;
}) {
  const intent = useQuery({
    queryKey: privateQueryKey('intent-history-detail', item?.id),
    enabled: !!item,
    queryFn: ({ signal }) =>
      getDownloadIntent({ intent_id: item?.id ?? '' }, { signal }),
    refetchInterval: (query) =>
      query.state.data && activeIntentStatuses.has(query.state.data.status)
        ? 2_000
        : false,
    refetchOnWindowFocus: true,
  });
  const snapshot = item ? intent.data : null;
  const jobId = snapshot?.status === 'handed_off' ? snapshot.job_id : null;
  const download = useQuery({
    queryKey: privateQueryKey('intent-history-download', jobId),
    enabled: !!item && !!jobId,
    queryFn: ({ signal }) => getDownload({ job_id: jobId ?? '' }, { signal }),
    refetchInterval: (query) =>
      query.state.data && activeDownloadStatuses.has(query.state.data.status)
        ? 3_000
        : false,
    refetchOnWindowFocus: true,
  });
  const job = jobId ? download.data : null;

  return (
    <Dialog open={!!item} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="max-h-[calc(100svh-2rem)] overflow-y-auto sm:max-w-xl"
        onCloseAutoFocus={(event) => {
          if (!triggerRef.current?.isConnected) return;
          event.preventDefault();
          triggerRef.current.focus();
        }}
        showCloseButton={false}
      >
        <DialogHeader>
          <DialogTitle className="text-xl">解析记录详情</DialogTitle>
          <DialogDescription className="break-words">
            {item?.title || '媒体解析'}
            {item ? (
              <>
                {' · '}
                <time dateTime={item.created_at}>
                  {new Date(item.created_at).toLocaleString('zh-CN', {
                    hour12: false,
                  })}
                </time>
              </>
            ) : null}
          </DialogDescription>
        </DialogHeader>

        {intent.isPending && item ? (
          <div role="status" className="flex flex-col gap-3 py-4">
            <span className="sr-only">正在读取解析详情</span>
            <Skeleton aria-hidden className="h-5 w-28" />
            <Skeleton aria-hidden className="h-4 w-4/5" />
          </div>
        ) : null}
        {intent.error && !snapshot ? (
          <PageErrorNotice
            compact
            title="暂时无法读取解析详情"
            message={displayError(intent.error)}
            onRetry={() => void intent.refetch()}
          />
        ) : null}
        {snapshot ? (
          <div className="flex flex-col gap-3 py-2">
            <Badge variant={intentStatusVariant(snapshot.status)}>
              {intentTitle(snapshot.status)}
            </Badge>
            <p className="text-sm leading-6 text-muted-foreground">
              {intentDescription(snapshot)}
            </p>
          </div>
        ) : null}

        {jobId && download.isPending ? (
          <div role="status" className="flex flex-col gap-3 py-4">
            <span className="sr-only">正在读取下载任务</span>
            <Skeleton aria-hidden className="aspect-video w-full" />
            <Skeleton aria-hidden className="h-4 w-3/5" />
          </div>
        ) : null}
        {jobId && download.error && !job ? (
          <PageErrorNotice
            compact
            title="暂时无法读取下载任务"
            message={displayError(download.error)}
            onRetry={() => void download.refetch()}
          />
        ) : null}
        {job ? (
          <div className="flex flex-col gap-4">
            <MediaCover
              alt={`${job.title || item?.title || '媒体'}封面`}
              className="rounded-md"
              fallback={{
                eyebrow: job.source_label,
                title: job.title || item?.title,
              }}
              src={job.thumbnail_url}
            />
            <div className="flex flex-col gap-2">
              <h3 className="text-base font-medium">
                {job.title || item?.title || '媒体下载任务'}
              </h3>
              <Badge variant={statusVariant(job.status)}>
                {statusLabels[job.status]}
              </Badge>
              <p className="text-sm leading-6 text-muted-foreground">
                {statusHeading(job)}。{statusDescription(job)}
              </p>
              {job.status === 'failed' ? (
                <p className="text-sm leading-6 text-destructive">
                  {failureDescription(job)}
                </p>
              ) : null}
              {activeDownloadStatuses.has(job.status) ? (
                <div className="flex flex-col gap-2 pt-2">
                  <div className="flex justify-between text-sm">
                    <span>{displayStage(job)}</span>
                    <span className="tabular-nums">{job.progress}%</span>
                  </div>
                  <Progress
                    aria-label={`下载进度 ${job.progress}%`}
                    value={job.progress}
                  />
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">关闭</Button>
          </DialogClose>
          {snapshot?.status === 'ready' && snapshot.inspection_id ? (
            <Button asChild>
              <Link
                href={`/downloads/new?inspectionId=${encodeURIComponent(snapshot.inspection_id)}&intentId=${encodeURIComponent(snapshot.id)}`}
              >
                查看解析结果
              </Link>
            </Button>
          ) : null}
          {job ? (
            <Button asChild>
              <Link
                href={`/downloads/detail?jobId=${encodeURIComponent(job.id)}`}
              >
                打开完整下载任务
              </Link>
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function intentDescription(intent: API.IntentResponse): string {
  if (intent.reason_code) {
    const reason = localizedErrorMessage(intent.reason_code);
    if (reason) return reason;
  }
  if (activeIntentStatuses.has(intent.status))
    return '任务仍在后台处理。关闭此窗口不会中断解析。';
  if (intent.status === 'handed_off')
    return intent.job_id
      ? '解析已完成，下载任务的最新状态显示在下方。'
      : '下载任务引用暂不可用，请刷新解析记录后重试。';
  if (intent.status === 'ready')
    return intent.inspection_id
      ? '解析结果已就绪，可进入结果页选择下载规格。'
      : '解析结果引用暂不可用，请刷新解析记录后重试。';
  if (intent.status === 'action_required') return '当前内容需要额外访问权限。';
  if (intent.status === 'failed') return '本次解析未完成。';
  if (intent.status === 'expired') return '本次解析已超时。';
  return '本次解析已取消。';
}
