import { DownloadSimple } from '@phosphor-icons/react';
import { Fragment } from 'react';

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
  ItemSeparator,
  ItemTitle,
} from '@/components/ui/item';
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
      {data?.items.length ? (
        <ItemGroup className="gap-0">
          {data.items.map((item) => (
            <Fragment key={item.id}>
              <HistoryRow item={item} onDownload={onDownload} onOpen={onOpen} />
              <ItemSeparator className="my-0" />
            </Fragment>
          ))}
        </ItemGroup>
      ) : null}
      {data && !data.items.length ? (
        <Empty className="min-h-64 rounded-none border-b py-16">
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
  onOpen,
}: {
  item: DownloadHistoryItem;
  onDownload: (item: DownloadHistoryItem) => void;
  onOpen: (id: string) => void;
}) {
  return (
    <Item
      className="grid gap-4 rounded-none border-0 px-0 py-5 sm:grid-cols-[112px_minmax(0,1fr)_auto] sm:items-center"
      role="listitem"
    >
      <ItemMedia>
        <MediaCover
          alt={`${item.title} 视频封面`}
          className="w-28"
          src={item.thumbnail_url}
        />
      </ItemMedia>
      <ItemContent className="min-w-0">
        <ItemTitle className="line-clamp-2">
          <Button
            aria-label={item.title}
            className="h-auto justify-start whitespace-normal p-0 text-left text-foreground hover:text-primary"
            onClick={() => onOpen(item.id)}
            size="sm"
            variant="link"
            type="button"
          >
            {item.title}
          </Button>
        </ItemTitle>
        <ItemDescription className="flex flex-wrap items-center gap-2">
          <span>{item.format_name}</span>
          <span>·</span>
          <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
        </ItemDescription>
      </ItemContent>
      <ItemActions className="w-full justify-between sm:w-auto sm:justify-end">
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
      </ItemActions>
    </Item>
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
