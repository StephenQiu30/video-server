import { ArrowClockwise, DownloadSimple } from '@phosphor-icons/react';
import Link from 'next/link';

import { DownloadDeleteDialog } from '@/components/downloads/download-delete-dialog';
import { downloadRecovery } from '@/components/downloads/download-state-model';
import MediaCover from '@/components/intake/media-cover';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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

export default function DownloadHistoryList({
  data,
  loading,
  onDownload,
  onDelete,
  onRetry,
  pendingAction,
}: {
  data: API.DownloadHistoryResponse | null;
  loading: boolean;
  onDownload: (item: API.DownloadHistoryItemResponse) => void;
  onDelete: (item: API.DownloadHistoryItemResponse) => Promise<void>;
  onRetry: (item: API.DownloadHistoryItemResponse) => void;
  pendingAction: { id: string; type: 'delete' | 'download' | 'retry' } | null;
}) {
  return (
    <div className="mt-4">
      {loading && !data ? <LoadingRows /> : null}
      {data?.items.length ? (
        <ItemGroup className="gap-2">
          {data.items.map((item) => (
            <HistoryRow
              item={item}
              key={item.id}
              onDownload={onDownload}
              onDelete={onDelete}
              onRetry={onRetry}
              pendingAction={pendingAction}
            />
          ))}
        </ItemGroup>
      ) : null}
      {data && !data.items.length ? (
        <PageEmptyNotice
          compact
          description="调整筛选条件，或新建一个下载任务。"
          icon={<DownloadSimple aria-hidden />}
          title="没有匹配的下载记录"
        />
      ) : null}
    </div>
  );
}

function HistoryRow({
  item,
  onDownload,
  onDelete,
  onRetry,
  pendingAction,
}: {
  item: API.DownloadHistoryItemResponse;
  onDownload: (item: API.DownloadHistoryItemResponse) => void;
  onDelete: (item: API.DownloadHistoryItemResponse) => Promise<void>;
  onRetry: (item: API.DownloadHistoryItemResponse) => void;
  pendingAction: { id: string; type: 'delete' | 'download' | 'retry' } | null;
}) {
  const detailHref = `/downloads/detail?jobId=${encodeURIComponent(item.id)}`;
  const canDownload = item.status === 'succeeded' && item.file_available;
  const recovery = downloadRecovery(item);
  const busy = pendingAction?.id === item.id;

  return (
    <Item
      className="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-x-4 gap-y-3 rounded-none border-0 px-0 py-5 sm:grid-cols-[128px_minmax(0,1fr)_auto] sm:gap-x-6 sm:py-6"
      role="listitem"
    >
      <Link
        aria-label={item.title}
        className="focus-ring group/summary col-span-2 grid min-w-0 grid-cols-[96px_minmax(0,1fr)] items-center gap-x-4 gap-y-3 rounded-md sm:col-span-2 sm:grid-cols-[128px_minmax(0,1fr)] sm:gap-x-6"
        href={detailHref}
      >
        <ItemMedia className="!translate-y-0 shrink-0 self-center group-has-data-[slot=item-description]/item:translate-y-0 group-has-data-[slot=item-description]/item:self-center">
          <MediaCover
            alt={`${item.title} 媒体封面`}
            className="w-24 rounded-md ring-0 sm:w-32"
            compact
            fallback={{
              detail: item.format_name,
              eyebrow: item.source_label,
              title: item.title,
            }}
            src={item.thumbnail_url}
          />
        </ItemMedia>
        <ItemContent className="min-w-0 gap-1.5">
          <ItemTitle className="line-clamp-2">
            <span className="line-clamp-2 text-[15px] leading-snug text-foreground transition-colors group-hover/summary:text-muted-foreground">
              {item.title}
            </span>
          </ItemTitle>
          <ItemDescription className="flex flex-wrap items-center gap-2 text-xs sm:text-sm">
            <span>{item.source_label}</span>
            <span aria-hidden>·</span>
            <span>{item.format_name}</span>
            <span aria-hidden>·</span>
            <time dateTime={item.created_at}>
              {formatDate(item.created_at)}
            </time>
            {item.status === 'succeeded' ? (
              <>
                <span aria-hidden>·</span>
                <span>{fileAvailabilityLabel(item)}</span>
              </>
            ) : null}
          </ItemDescription>
        </ItemContent>
      </Link>
      <ItemActions className="col-span-2 w-full justify-between gap-1 sm:col-auto sm:w-auto sm:justify-end">
        <Badge
          className="rounded-md px-2 py-1 font-normal"
          variant={statusVariant(item.status)}
        >
          {downloadStatusLabels[item.status]}
          {activeStatuses.has(item.status) ? ` · ${item.progress}%` : ''}
        </Badge>
        <div className="flex items-center gap-1">
          {canDownload ? (
            <Button
              disabled={busy}
              onClick={() => onDownload(item)}
              size="sm"
              variant="ghost"
            >
              {busy && pendingAction?.type === 'download' ? (
                <Spinner aria-hidden data-icon="inline-start" />
              ) : (
                <DownloadSimple data-icon="inline-start" />
              )}
              获取文件
            </Button>
          ) : recovery === 'reimport' ? (
            <Button asChild size="sm" variant="ghost">
              <Link href="/">返回首页重新导入</Link>
            </Button>
          ) : recovery === 'retry' ? (
            <Button
              disabled={busy}
              onClick={() => onRetry(item)}
              size="sm"
              variant="ghost"
            >
              {busy && pendingAction?.type === 'retry' ? (
                <Spinner aria-hidden data-icon="inline-start" />
              ) : (
                <ArrowClockwise data-icon="inline-start" />
              )}
              重新下载
            </Button>
          ) : (
            <Button asChild size="sm" variant="ghost">
              <Link href={detailHref}>查看任务</Link>
            </Button>
          )}
          <DownloadDeleteDialog
            active={activeStatuses.has(item.status)}
            busy={busy}
            compact
            onDelete={() => onDelete(item)}
          />
        </div>
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
      <div aria-hidden className="flex flex-col gap-2">
        {['first', 'second', 'third'].map((key) => (
          <div
            className="grid grid-cols-[96px_minmax(0,1fr)] items-center gap-4 py-5 sm:grid-cols-[128px_minmax(0,1fr)_auto] sm:gap-6 sm:py-6"
            key={key}
          >
            <Skeleton className="h-16 w-24 rounded-md sm:w-32" />
            <div className="flex flex-col gap-2">
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

function fileAvailabilityLabel(item: API.DownloadHistoryItemResponse) {
  return item.file_available ? '文件持久保存' : '文件已清理';
}

function statusVariant(
  status: API.DownloadStatus,
): 'secondary' | 'default' | 'secondary' | 'destructive' {
  if (status === 'succeeded') return 'default';
  if (status === 'failed') return 'destructive';
  if (activeStatuses.has(status)) return 'secondary';
  return 'secondary';
}

export const downloadStatusLabels: Record<API.DownloadStatus, string> = {
  queued: '排队中',
  running: '下载中',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

const activeStatuses = new Set<API.DownloadStatus>([
  'queued',
  'running',
  'retry_wait',
]);

const historyDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
  timeStyle: 'short',
});
