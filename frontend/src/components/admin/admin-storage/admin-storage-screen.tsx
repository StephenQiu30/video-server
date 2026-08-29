import { ArrowClockwise, CheckCircle, Trash } from '@phosphor-icons/react';

import { BackLink } from '@/components/layout/back-link';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';

import { STORAGE_PAGE_SIZE } from './model';
import { StorageCleanupDialog } from './storage-cleanup-dialog';
import { StorageFileList } from './storage-file-list';

type AdminStorageScreenProps = {
  items: API.StoredFileResponse[];
  total: number;
  page: number;
  loading: boolean;
  error: string;
  notice: string;
  cleanup: {
    open: boolean;
    days: number;
    cleaning: boolean;
    error: string;
  };
  onPageChange: (page: number) => void;
  onRetry: () => void;
  onOpenCleanup: () => void;
  onCloseCleanup: () => void;
  onCleanupDaysChange: (days: number) => void;
  onConfirmCleanup: () => void;
};

export function AdminStorageScreen({
  items,
  total,
  page,
  loading,
  error,
  notice,
  cleanup,
  onPageChange,
  onRetry,
  onOpenCleanup,
  onCloseCleanup,
  onCleanupDaysChange,
  onConfirmCleanup,
}: AdminStorageScreenProps) {
  const pages = Math.max(1, Math.ceil(total / STORAGE_PAGE_SIZE));
  const first = total === 0 ? 0 : (page - 1) * STORAGE_PAGE_SIZE + 1;
  const last = Math.min(page * STORAGE_PAGE_SIZE, total);

  return (
    <section aria-busy={loading} className="space-y-10">
      <div>
        <BackLink className="mb-4" fallbackHref="/account" />
        <PageHeader
          action={
            <Button onClick={onOpenCleanup} variant="destructive">
              <Trash aria-hidden />
              清理历史文件
            </Button>
          }
          description="文件默认持久保存，不会自动过期。管理员可在确认后手动清理指定天数前的文件。"
          title="文件管理"
        />
      </div>

      {notice ? (
        <Alert variant="success">
          <CheckCircle aria-hidden />
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      ) : null}

      {loading && items.length === 0 ? (
        <div className="space-y-4 border-y py-5">
          {['one', 'two', 'three', 'four', 'five'].map((key) => (
            <Skeleton className="h-14 w-full" key={key} />
          ))}
        </div>
      ) : error ? (
        <Alert variant="destructive">
          <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
            <span>{error}</span>
            <Button onClick={onRetry} size="sm" variant="outline">
              <ArrowClockwise aria-hidden />
              重试
            </Button>
          </AlertDescription>
        </Alert>
      ) : items.length === 0 ? (
        <Empty className="hairline min-h-64 items-start rounded-none border-y py-14 text-left">
          <EmptyHeader className="items-start">
            <EmptyTitle>暂无持久文件</EmptyTitle>
            <EmptyDescription className="text-left">
              完成下载、剧本解析或报告生成后，文件会显示在这里。
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <StorageFileList items={items} />
      )}

      {!error && total > 0 ? (
        <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
          <span>
            显示 {first}–{last}，共 {total} 项
          </span>
          <PagePagination
            ariaLabel="文件列表分页"
            className="w-auto justify-end"
            compact
            onPageChange={onPageChange}
            page={page}
            pages={pages}
          />
        </footer>
      ) : null}

      <StorageCleanupDialog
        cleaning={cleanup.cleaning}
        days={cleanup.days}
        error={cleanup.error}
        onClose={onCloseCleanup}
        onConfirm={onConfirmCleanup}
        onDaysChange={onCleanupDaysChange}
        open={cleanup.open}
      />
    </section>
  );
}
