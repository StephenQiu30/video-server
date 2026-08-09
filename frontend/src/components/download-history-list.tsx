import { DownloadSimple } from '@phosphor-icons/react';

import MediaCover from '@/components/media-cover';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import type {
  DownloadHistory,
  DownloadHistoryItem,
  DownloadStatus,
} from '@/types/video';

export default function DownloadHistoryList({
  data,
  loading,
  onDownload,
  onOpen,
}: {
  data: DownloadHistory | null;
  loading: boolean;
  onDownload: (item: DownloadHistoryItem) => void;
  onOpen: (id: string) => void;
}) {
  return (
    <section aria-label="下载任务" className="mt-3 border-t">
      {loading && !data ? <LoadingRows /> : null}
      {data?.items.map((item) => (
        <HistoryRow
          item={item}
          key={item.id}
          onDownload={onDownload}
          onOpen={onOpen}
        />
      ))}
      {data && !data.items.length ? (
        <div className="py-20 text-center">
          <p className="text-lg font-medium">没有匹配的下载记录</p>
          <p className="mt-2 text-sm text-muted-foreground">
            调整筛选条件，或新建一个下载任务。
          </p>
        </div>
      ) : null}
    </section>
  );
}

function HistoryRow({
  item,
  onDownload,
  onOpen,
}: {
  item: DownloadHistoryItem;
  onDownload: (item: DownloadHistoryItem) => void;
  onOpen: (id: string) => void;
}) {
  return (
    <article className="grid gap-4 border-b py-5 sm:grid-cols-[112px_minmax(0,1fr)_auto] sm:items-center">
      <MediaCover
        alt={`${item.title} 视频封面`}
        className="w-28"
        src={item.thumbnail_url}
      />
      <div className="min-w-0">
        <button
          className="focus-ring line-clamp-2 rounded text-left font-medium hover:text-primary"
          onClick={() => onOpen(item.id)}
          type="button"
        >
          {item.title}
        </button>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>{item.format_name}</span>
          <span>·</span>
          <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 sm:justify-end">
        <Badge variant={statusVariant(item.status)}>
          {downloadStatusLabels[item.status]}
          {activeStatuses.has(item.status) ? ` · ${item.progress}%` : ''}
        </Badge>
        {item.status === 'succeeded' ? (
          <Button onClick={() => onDownload(item)} size="sm" variant="ghost">
            <DownloadSimple size={16} />
            获取文件
          </Button>
        ) : (
          <Button onClick={() => onOpen(item.id)} size="sm" variant="ghost">
            查看任务
          </Button>
        )}
      </div>
    </article>
  );
}

function LoadingRows() {
  return ['first', 'second', 'third'].map((key) => (
    <Skeleton className="my-5 h-24 w-full" key={key} />
  ));
}

function formatDate(value: string) {
  return historyDateFormatter.format(new Date(value));
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
