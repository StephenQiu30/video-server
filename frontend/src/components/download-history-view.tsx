'use client';

import { ArrowClockwise, MagnifyingGlass, Plus } from '@phosphor-icons/react';
import Link from 'next/link';
import { useState } from 'react';

import { BackLink } from '@/components/back-link';
import DownloadHistoryList, {
  downloadStatusLabels,
} from '@/components/download-history-list';
import { PageHeader } from '@/components/page-header';
import { PagePagination } from '@/components/page-pagination';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Field, FieldLabel } from '@/components/ui/field';
import {
  InputGroup,
  InputGroupAddon,
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
  displayError,
  issueDownloadUrl,
  triggerBrowserDownload,
} from '@/services/download';
import type { DownloadHistoryItem, DownloadStatus } from '@/types/video';

export default function DownloadHistoryView() {
  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState('');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<DownloadStatus | undefined>();
  const [actionError, setActionError] = useState<string | null>(null);
  const state = useDownloadHistory({
    page,
    page_size: 20,
    search: search || undefined,
    status,
  });

  async function download(item: DownloadHistoryItem) {
    setActionError(null);
    try {
      triggerBrowserDownload((await issueDownloadUrl(item.id)).url);
    } catch (reason) {
      setActionError(displayError(reason));
    }
  }

  return (
    <main className="content-shell py-14 sm:py-20 lg:py-24">
      <BackLink className="mb-7" fallbackHref="/" />
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
        title="下载历史"
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
              搜索下载历史
            </FieldLabel>
            <InputGroup className="h-11 border-0 bg-surface">
              <InputGroupInput
                className="h-full"
                id="history-search"
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="按视频标题搜索"
                value={searchInput}
              />
              <InputGroupAddon>
                <MagnifyingGlass aria-hidden />
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

      {state.data ? (
        <p
          aria-live="polite"
          className="mt-12 font-mono text-xs text-muted-foreground"
        >
          共 {state.data.total} 项 · 已完成 {state.data.summary.succeeded} ·
          进行中 {state.data.summary.active}
        </p>
      ) : null}
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
      />

      {state.data && state.data.total > state.data.page_size ? (
        <PagePagination
          ariaLabel="下载历史分页"
          className="mt-10 justify-end"
          onPageChange={setPage}
          page={page}
          pages={Math.ceil(state.data.total / state.data.page_size)}
        />
      ) : null}
    </main>
  );
}
