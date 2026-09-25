import { ArrowClockwise, DownloadSimple } from '@phosphor-icons/react';
import Link from 'next/link';
import { DownloadDeleteDialog } from '@/components/downloads/download-delete-dialog';
import {
  DownloadStatusCode,
  downloadRecovery,
  downloadStatusLabels,
  isActiveDownloadStatus,
  statusVariant,
} from '@/components/downloads/download-state-model';
import type { DownloadAction } from '@/components/downloads/use-download-actions';
import { DataTable } from '@/components/layout/data-table';
import { PageEmptyNotice } from '@/components/layout/page-empty-notice';
import MediaCover from '@/components/media/media-cover';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';

export default function DownloadHistoryList({
  data,
  loading,
  onDownload,
  onDelete,
  onRetry,
  pendingActions,
  selection,
}: {
  data: API.DownloadHistoryResponse | null;
  loading: boolean;
  onDownload: (item: API.DownloadHistoryItemResponse) => void;
  onDelete: (item: API.DownloadHistoryItemResponse) => Promise<void>;
  onRetry: (item: API.DownloadHistoryItemResponse) => void;
  selection?: {
    ids: string[];
    busy: boolean;
    toggle: (id: string, checked: boolean) => void;
  };
  pendingActions: Array<{ id: string; type: DownloadAction }>;
}) {
  return (
    <div className="mt-4">
      {loading && !data ? <LoadingRows /> : null}
      {data?.items.length ? (
        <DataTable<API.DownloadHistoryItemResponse>
          caption="下载记录"
          data={data.items}
          getRowId={(item) => item.id}
          getRowLabel={(item) => item.title}
          className="min-w-[760px]"
          selection={
            selection
              ? {
                  ...selection,
                  eligible: (id) =>
                    !pendingActions.some((action) => action.id === id),
                }
              : undefined
          }
          columns={[
            {
              id: 'content',
              header: '内容',
              className: 'whitespace-normal',
              hideable: false,
              cell: (item) => <HistoryContent item={item} />,
            },
            {
              id: 'status',
              header: '状态',
              className: 'w-32',
              cell: (item) => (
                <Badge variant={statusVariant(item.status)}>
                  {downloadStatusLabels[item.status]}
                  {isActiveDownloadStatus(item.status)
                    ? ` · ${item.progress}%`
                    : ''}
                </Badge>
              ),
            },
            {
              id: 'actions',
              header: '操作',
              className: 'w-[240px] text-right',
              hideable: false,
              cell: (item) => (
                <HistoryActions
                  item={item}
                  onDownload={onDownload}
                  onDelete={onDelete}
                  onRetry={onRetry}
                  selection={selection}
                  pendingAction={
                    pendingActions.find((action) => action.id === item.id) ??
                    null
                  }
                />
              ),
            },
          ]}
        />
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

function HistoryContent({ item }: { item: API.DownloadHistoryItemResponse }) {
  const detailHref = `/downloads/detail?jobId=${encodeURIComponent(item.id)}`;
  return (
    <Link
      aria-label={item.title}
      className="focus-ring grid min-w-0 grid-cols-[64px_minmax(0,1fr)] items-center gap-3 sm:grid-cols-[96px_minmax(0,1fr)]"
      href={detailHref}
    >
      <div>
        <MediaCover
          alt={`${item.title} 媒体封面`}
          className="w-16 sm:w-24"
          compact
          fallback={{
            detail: item.format_name,
            eyebrow: item.source_label,
            title: item.title,
          }}
          src={item.thumbnail_url}
        />
      </div>
      <div className="min-w-0 gap-1.5">
        <div className="line-clamp-2">
          <span className="line-clamp-2">{item.title}</span>
        </div>
        <div className="text-muted-foreground">
          <span>{item.source_label}</span>
          <span aria-hidden> · </span>
          <span>{item.format_name}</span>
          <span aria-hidden> · </span>
          <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
          {item.status === DownloadStatusCode.Succeeded ? (
            <>
              <span aria-hidden> · </span>
              <span>{fileAvailabilityLabel(item)}</span>
            </>
          ) : null}
        </div>
      </div>
    </Link>
  );
}

function HistoryActions({
  item,
  onDownload,
  onDelete,
  onRetry,
  pendingAction,
  selection,
}: {
  item: API.DownloadHistoryItemResponse;
  onDownload: (item: API.DownloadHistoryItemResponse) => void;
  onDelete: (item: API.DownloadHistoryItemResponse) => Promise<void>;
  onRetry: (item: API.DownloadHistoryItemResponse) => void;
  selection?: {
    ids: string[];
    busy: boolean;
    toggle: (id: string, checked: boolean) => void;
  };
  pendingAction: { id: string; type: DownloadAction } | null;
}) {
  const detailHref = `/downloads/detail?jobId=${encodeURIComponent(item.id)}`;
  const canDownload =
    item.status === DownloadStatusCode.Succeeded && item.file_available;
  const recovery = downloadRecovery(item);
  const busy = Boolean(selection?.busy || pendingAction);

  return (
    <div className="flex items-center justify-end gap-1">
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
        active={isActiveDownloadStatus(item.status)}
        busy={pendingAction?.type === 'delete'}
        disabled={busy}
        compact
        onDelete={() => onDelete(item)}
      />
    </div>
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
            <Skeleton className="h-16 w-24 sm:w-32" />
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

const historyDateFormatter = new Intl.DateTimeFormat('zh-CN', {
  dateStyle: 'medium',
  timeStyle: 'short',
});
