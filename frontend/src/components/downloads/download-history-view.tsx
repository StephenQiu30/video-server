'use client';

import { ArrowClockwise, MagnifyingGlass, Plus } from '@phosphor-icons/react';
import Link from 'next/link';
import { useRef, useState } from 'react';
import DownloadHistoryList, {
  downloadStatusLabels,
} from '@/components/downloads/download-history-list';
import { DownloadHistorySummary } from '@/components/downloads/download-history-summary';
import { BackLink } from '@/components/layout/back-link';
import { markNavigationPush } from '@/components/layout/navigation-history';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Field, FieldLabel } from '@/components/ui/field';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDownloadHistory } from '@/hooks/useDownloadHistory';
import {
  createIdempotencyKey,
  deleteDownload,
  displayError,
  issueDownloadUrl,
  retryDownload,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';

export default function DownloadHistoryView() {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<DownloadStatus | undefined>();
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<{
    id: string;
    type: 'delete' | 'download' | 'retry';
  } | null>(null);
  const retryKeys = useRef(new Map<string, string>());
  const state = useDownloadHistory({
    page,
    page_size: 20,
    search: search || undefined,
    status,
  });

  async function download(item: DownloadHistoryItem) {
    setActionError(null);
    setPendingAction({ id: item.id, type: 'download' });
    try {
      const result = await issueDownloadUrl(item.id);
      triggerBrowserDownload(result.url, result.filename);
    } catch (reason) {
      setActionError(displayError(reason));
    } finally {
      setPendingAction(null);
    }
  }

  async function retry(item: DownloadHistoryItem) {
    setActionError(null);
    setPendingAction({ id: item.id, type: 'retry' });
    const key = retryKeys.current.get(item.id) ?? createIdempotencyKey();
    retryKeys.current.set(item.id, key);
    try {
      const retried = await retryDownload(item.id, key);
      const target = `/downloads/detail?jobId=${encodeURIComponent(retried.id)}`;
      markNavigationPush(target);
      window.location.assign(target);
    } catch (reason) {
      setActionError(displayError(reason));
      setPendingAction(null);
    }
  }

  async function remove(item: DownloadHistoryItem) {
    setActionError(null);
    setPendingAction({ id: item.id, type: 'delete' });
    try {
      await deleteDownload(item.id);
      state.retry();
    } catch (reason) {
      setActionError(displayError(reason));
    } finally {
      setPendingAction(null);
    }
  }

  return (
    <div className="inner-page">
      <BackLink className="mb-4" fallbackHref="/" />
      <PageHeader
        action={
          <Button asChild size="lg">
            <Link href="/">
              <Plus size={17} />
              新建下载
            </Link>
          </Button>
        }
        description="继续查看、获取或分析已创建的任务。"
        title="下载记录"
      />

      <div className="mt-12 grid gap-2 sm:grid-cols-[minmax(0,1fr)_11rem_auto] sm:items-end lg:mt-16">
        <form
          className="min-w-0"
          onSubmit={(event) => {
            event.preventDefault();
            setPage(1);
            setSearch(searchInput.trim());
          }}
        >
          <Field>
            <FieldLabel className="sr-only" htmlFor="history-search">
              搜索下载记录
            </FieldLabel>
            <InputGroup className="h-11 border-0 bg-surface">
              <InputGroupInput
                className="h-full"
                id="history-search"
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="按视频标题搜索"
                value={searchInput}
              />
              <InputGroupAddon align="inline-end">
                <InputGroupButton
                  aria-label="搜索下载记录"
                  className="size-11"
                  size="icon-sm"
                  type="submit"
                >
                  <MagnifyingGlass aria-hidden />
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </Field>
        </form>
        <Field>
          <FieldLabel className="sr-only" htmlFor="history-status">
            按状态筛选
          </FieldLabel>
          <Select
            onValueChange={(value) => {
              setPage(1);
              setStatus(
                value === 'all' ? undefined : (value as DownloadStatus),
              );
            }}
            value={status ?? 'all'}
          >
            <SelectTrigger
              className="h-11 w-full border-0 bg-surface"
              id="history-status"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              {Object.entries(downloadStatusLabels).map(([value, label]) => (
                <SelectItem key={value} value={value}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Button
          className="h-11 border-0 bg-surface px-4"
          onClick={state.retry}
          type="button"
          variant="outline"
        >
          <ArrowClockwise size={17} />
          刷新
        </Button>
      </div>

      <DownloadHistorySummary data={state.data} loading={state.loading} />
      {state.error || actionError ? (
        <Alert className="mt-6" variant="destructive">
          <AlertTitle>操作未完成</AlertTitle>
          <AlertDescription>{state.error ?? actionError}</AlertDescription>
        </Alert>
      ) : null}

      <DownloadHistoryList
        data={state.data}
        loading={state.loading}
        onDownload={(item) => void download(item)}
        onDelete={remove}
        onRetry={(item) => void retry(item)}
        pendingAction={pendingAction}
      />

      {state.data && state.data.total > state.data.page_size ? (
        <PagePagination
          ariaLabel="下载记录分页"
          className="mt-10 justify-end"
          onPageChange={setPage}
          page={page}
          pages={Math.ceil(state.data.total / state.data.page_size)}
        />
      ) : null}
    </div>
  );
}
