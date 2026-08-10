import { ArrowClockwise, DownloadSimple } from '@phosphor-icons/react';
import Link from 'next/link';

import MediaCover from '@/components/media-cover';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import type {
  DownloadHistory,
  DownloadHistoryItem,
  DownloadStatus,
} from '@/types/video';

export default function DownloadHistoryList({
  data,
  loading,
  onDownload,
  onRetry,
  pendingAction,
}: {
  data: DownloadHistory | null;
  loading: boolean;
  onDownload: (item: DownloadHistoryItem) => void;
  onRetry: (item: DownloadHistoryItem) => void;
  pendingAction: { id: string; type: 'download' | 'retry' } | null;
}) {
  return (
    <section aria-label="下载任务" className="mt-4 border-t border-border/70">
      {loading && !data ? <LoadingRows /> : null}
      {data?.items.length ? (
        <ItemGroup className="gap-0 divide-y divide-border/70">
          {data.items.map((item) => (
            <HistoryRow
              item={item}
              key={item.id}
              onDownload={onDownload}
              onRetry={onRetry}
              pendingAction={pendingAction}
            />
          ))}
        </ItemGroup>
      ) : null}
      {data && !data.items.length ? (
        <Empty className="min-h-72 rounded-none border-0 py-20">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <DownloadSimple aria-hidden />
            </EmptyMedia>
            <EmptyTitle>没有匹配的下载记录</EmptyTitle>
            <EmptyDescription>
              调整筛选条件，或新建一个下载任务。
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : null}
    </section>
  );
}

function HistoryRow({
  item,
  onDownload,
  onRetry,
  pendingAction,
}: {
  item: DownloadHistoryItem;
  onDownload: (item: DownloadHistoryItem) => void;
  onRetry: (item: DownloadHistoryItem) => void;
  pendingAction: { id: string; type: 'download' | 'retry' } | null;
}) {
  const detailHref = `/downloads/detail?jobId=${encodeURIComponent(item.id)}`;
  const canDownload = item.status === 'succeeded' && item.file_available;
  const canRetry =
    ['failed', 'cancelled'].includes(item.status) ||
    (item.status === 'succeeded' && !item.file_available);
  const busy = pendingAction?.id === item.id;

  return (
    <Item
      className="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-x-4 gap-y-3 rounded-none border-0 px-0 py-5 sm:grid-cols-[128px_minmax(0,1fr)_auto] sm:gap-x-6 sm:py-6"
      role="listitem"
    >
      <ItemMedia className="self-center">
        <MediaCover
          alt={`${item.title} 视频封面`}
          className="w-24 rounded-md ring-0 sm:w-32"
          src={item.thumbnail_url}
        />
      </ItemMedia>
      <ItemContent className="min-w-0 gap-1.5">
        <ItemTitle className="line-clamp-2">
          <Button
            asChild
            className="h-auto justify-start whitespace-normal p-0 text-left text-[15px] leading-snug text-foreground hover:text-muted-foreground hover:no-underline"
            size="sm"
            variant="link"
          >
            <Link href={detailHref}>{item.title}</Link>
          </Button>
        </ItemTitle>
        <ItemDescription className="flex flex-wrap items-center gap-2 text-xs sm:text-sm">
          <span>{item.format_name}</span>
          <span aria-hidden>·</span>
          <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
          {item.status === 'succeeded' ? (
            <>
              <span aria-hidden>·</span>
              <span>{fileAvailabilityLabel(item)}</span>
            </>
          ) : null}
        </ItemDescription>
      </ItemContent>
      <ItemActions className="col-span-2 w-full justify-between sm:col-auto sm:w-auto sm:justify-end">
        <Badge
          className="rounded-md px-2 py-1 font-normal"
          variant={statusVariant(item.status)}
        >
          {downloadStatusLabels[item.status]}
          {activeStatuses.has(item.status) ? ` · ${item.progress}%` : ''}
        </Badge>
        {canDownload ? (
          <Button
            className="-mr-2"
            disabled={busy}
            onClick={() => onDownload(item)}
            size="sm"
            variant="ghost"
          >
            {busy && pendingAction?.type === 'download' ? (
              <Spinner aria-hidden />
            ) : (
              <DownloadSimple size={16} />
            )}
            获取文件
          </Button>
        ) : canRetry ? (
          <Button
            className="-mr-2"
            disabled={busy}
            onClick={() => onRetry(item)}
            size="sm"
            variant="ghost"
          >
            {busy && pendingAction?.type === 'retry' ? (
              <Spinner aria-hidden />
            ) : (
              <ArrowClockwise size={16} />
            )}
            重新下载
          </Button>
        ) : (
          <Button asChild className="-mr-2" size="sm" variant="ghost">
            <Link href={detailHref}>查看任务</Link>
          </Button>
        )}
      </ItemActions>
    </Item>
  );
}

function LoadingRows() {
  return (
    <>
      <span className="sr-only" role="status">
        正在加载下载记录
      </span>
      <div aria-hidden className="divide-y divide-border/70">
        {['first', 'second', 'third'].map((key) => (
          <div
            className="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-4 py-5 sm:grid-cols-[128px_minmax(0,1fr)_auto] sm:gap-6 sm:py-6"
            key={key}
          >
            <Skeleton className="aspect-video w-24 rounded-md sm:w-32" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-2/5" />
              <Skeleton className="h-3 w-3/5" />
            </div>
            <Skeleton className="col-span-2 h-7 w-28 justify-self-end sm:col-auto" />
          </div>
        ))}
      </div>
    </>
  );
}

function formatDate(value: string) {
  return historyDateFormatter.format(new Date(value));
}

function fileAvailabilityLabel(item: DownloadHistoryItem) {
  if (!item.file_available) return '文件已过期';
  return item.file_expires_at
    ? `文件保留至 ${formatDate(item.file_expires_at)}`
    : '文件可下载';
}

function statusVariant(
  status: DownloadStatus,
): 'neutral' | 'success' | 'warning' | 'destructive' {
  if (status === 'succeeded') return 'success';
  if (status === 'failed') return 'destructive';
  if (activeStatuses.has(status)) return 'warning';
  return 'neutral';
}

export const downloadStatusLabels: Record<DownloadStatus, string> = {
  queued: '排队中',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const activeStatuses = new Set<DownloadStatus>([
  'queued',
  'running',
  'retry_wait',
]);

const historyDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
  timeStyle: 'short',
});
