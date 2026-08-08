import { DownloadSimpleIcon } from '@phosphor-icons/react';

import MediaCover from '@/components/media-cover';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type {
  DownloadHistory,
  DownloadHistoryItem,
  DownloadStatus,
} from '@/types/video';

type DownloadHistoryTableProps = {
  data: DownloadHistory | null;
  loading: boolean;
  onDownload: (item: DownloadHistoryItem) => void;
  onOpen: (id: string) => void;
};

export default function DownloadHistoryTable({
  data,
  loading,
  onDownload,
  onOpen,
}: DownloadHistoryTableProps) {
  return (
    <div className="mt-7 overflow-hidden rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>视频</TableHead>
            <TableHead>格式</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>创建时间</TableHead>
            <TableHead className="text-right">操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading && !data ? <LoadingRows /> : null}
          {data?.items.map((item) => (
            <HistoryRow
              item={item}
              key={item.id}
              onDownload={onDownload}
              onOpen={() => onOpen(item.id)}
            />
          ))}
          {data && !data.items.length ? (
            <TableRow>
              <TableCell
                className="h-32 text-center text-muted-foreground"
                colSpan={5}
              >
                没有匹配的下载记录
              </TableCell>
            </TableRow>
          ) : null}
        </TableBody>
      </Table>
    </div>
  );
}

function HistoryRow({
  item,
  onDownload,
  onOpen,
}: {
  item: DownloadHistoryItem;
  onDownload: (item: DownloadHistoryItem) => void;
  onOpen: () => void;
}) {
  return (
    <TableRow>
      <TableCell>
        <div className="flex min-w-64 items-center gap-3">
          <MediaCover
            alt={`${item.title} 视频封面`}
            className="w-24 shrink-0"
            src={item.thumbnail_url}
          />
          <button
            className="text-left font-medium hover:underline"
            onClick={onOpen}
            type="button"
          >
            {item.title}
          </button>
        </div>
      </TableCell>
      <TableCell>{item.format_name}</TableCell>
      <TableCell>
        <Badge variant="outline">
          {downloadStatusLabels[item.status]}
          {activeStatuses.has(item.status) ? ` · ${item.progress}%` : ''}
        </Badge>
      </TableCell>
      <TableCell className="font-mono text-xs text-muted-foreground">
        {new Intl.DateTimeFormat('zh-CN', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }).format(new Date(item.created_at))}
      </TableCell>
      <TableCell className="text-right">
        {item.status === 'succeeded' ? (
          <Button onClick={() => onDownload(item)} size="sm" variant="ghost">
            <DownloadSimpleIcon data-icon="inline-start" /> 获取文件
          </Button>
        ) : (
          <Button onClick={onOpen} size="sm" variant="ghost">
            查看任务
          </Button>
        )}
      </TableCell>
    </TableRow>
  );
}

function LoadingRows() {
  return ['first', 'second', 'third'].map((key) => (
    <TableRow key={key}>
      <TableCell colSpan={5}>
        <Skeleton className="h-14 w-full" />
      </TableCell>
    </TableRow>
  ));
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
