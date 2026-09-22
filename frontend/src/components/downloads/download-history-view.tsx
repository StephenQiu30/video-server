'use client';

import { ArrowClockwise, MagnifyingGlass, Plus } from '@phosphor-icons/react';
import { useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import {
  deleteDownload,
  issueDownloadUrl,
  retryDownload,
} from '@/api/downloads';
import DownloadHistoryList, {
  downloadStatusLabels,
} from '@/components/downloads/download-history-list';
import { DownloadHistorySummary } from '@/components/downloads/download-history-summary';
import { useDownloadHistory } from '@/components/downloads/use-download-history';
import { BackLink } from '@/components/layout/back-link';
import { FeedbackNotice } from '@/components/layout/feedback-notice';
import { markNavigationPush } from '@/components/layout/navigation-history';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { useWorkspaceState } from '@/components/layout/workspace-state-provider';
import { Button } from '@/components/ui/button';
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field';
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { triggerBrowserDownload } from '@/lib/browser-download';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';

import { createUuid as createIdempotencyKey } from '@/lib/uuid';

export default function DownloadHistoryView() {
  const queries = useQueryClient();
  const router = useRouter();
  const { history, setHistory } = useWorkspaceState();
  const { page, searchInput, search, status } = history;
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
  const responsePage = state.data?.page;
  const lastPage = state.data
    ? Math.max(1, Math.ceil(state.data.total / state.data.page_size))
    : page;
  useEffect(() => {
    // Placeholder data belongs to the previous filter/page and cannot clamp a
    // new request. Correct only an authoritative response for this page.
    if (responsePage === page && page > lastPage) {
      setHistory((current) => ({ ...current, page: lastPage }));
    }
  }, [lastPage, page, responsePage, setHistory]);

  function applySearch() {
    setHistory((current) => ({
      ...current,
      page: 1,
      search: current.searchInput.trim(),
    }));
  }

  async function download(item: API.DownloadHistoryItemResponse) {
    setActionError(null);
    setPendingAction({ id: item.id, type: 'download' });
    try {
      const result = await issueDownloadUrl(
        {
          job_id: encodeURIComponent(item.id),
          preview: false,
        },
        {
          headers: { 'X-FrameFetch-Download-Client': 'local-web' },
        },
      );
      triggerBrowserDownload(result.url, result.filename);
    } catch (reason) {
      setActionError(displayError(reason));
    } finally {
      setPendingAction(null);
    }
  }

  async function retry(item: API.DownloadHistoryItemResponse) {
    setActionError(null);
    setPendingAction({ id: item.id, type: 'retry' });
    const key = retryKeys.current.get(item.id) ?? createIdempotencyKey();
    retryKeys.current.set(item.id, key);
    try {
      const retried = await retryDownload(
        { job_id: encodeURIComponent(item.id) },
        { headers: { 'Idempotency-Key': key } },
      );
      const target = `/downloads/detail?jobId=${encodeURIComponent(retried.id)}`;
      void queries.invalidateQueries({
        queryKey: privateQueryKey('download-history'),
      });
      queries.setQueryData(privateQueryKey('download', retried.id), retried);
      markNavigationPush(target);
      router.push(target);
    } catch (reason) {
      setActionError(displayError(reason));
      setPendingAction(null);
    }
  }

  async function remove(item: API.DownloadHistoryItemResponse) {
    setActionError(null);
    setPendingAction({ id: item.id, type: 'delete' });
    try {
      await deleteDownload({ job_id: encodeURIComponent(item.id) });
      const detailKey = privateQueryKey('download', item.id);
      const analysisKey = privateQueryKey('analysis', 'video', item.id);
      await Promise.all([
        queries.cancelQueries({ queryKey: detailKey }),
        queries.cancelQueries({ queryKey: analysisKey }),
      ]);
      queries.removeQueries({ queryKey: detailKey });
      queries.removeQueries({ queryKey: analysisKey });
      void queries.invalidateQueries({
        queryKey: privateQueryKey('download-history'),
      });
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
            <Link href="/downloads/new">
              <Plus data-icon="inline-start" />
              新建下载
            </Link>
          </Button>
        }
        description="继续查看、获取或分析已创建的任务。"
        title="下载记录"
      />

      <FieldGroup className="mt-12 grid gap-3 sm:grid-cols-[minmax(0,1fr)_11rem_auto] sm:items-end lg:mt-16">
        <Field>
          <FieldLabel className="sr-only" htmlFor="history-search">
            搜索下载记录
          </FieldLabel>
          <InputGroup>
            <InputGroupInput
              className="h-full"
              id="history-search"
              onChange={(event) => {
                const searchInput = event.target.value;
                setHistory((current) => ({ ...current, searchInput }));
              }}
              onKeyDown={(event) => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                applySearch();
              }}
              placeholder="按视频标题搜索"
              value={searchInput}
            />
            <InputGroupAddon align="inline-end">
              <InputGroupButton
                aria-label="搜索下载记录"
                onClick={applySearch}
                size="icon-sm"
                type="button"
              >
                <MagnifyingGlass aria-hidden data-icon="inline-start" />
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </Field>
        <Field>
          <FieldLabel className="sr-only" htmlFor="history-status">
            按状态筛选
          </FieldLabel>
          <Select
            onValueChange={(value) => {
              setHistory((current) => ({
                ...current,
                page: 1,
                status:
                  value === 'all' ? undefined : (value as API.DownloadStatus),
              }));
            }}
            value={status ?? 'all'}
          >
            <SelectTrigger className="w-full" id="history-status">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="all">全部状态</SelectItem>
                {Object.entries(downloadStatusLabels).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </Field>
        <Button
          className="w-full sm:w-auto"
          aria-busy={state.refreshing}
          disabled={state.refreshing}
          onClick={state.retry}
          type="button"
          variant="outline"
        >
          <ArrowClockwise data-icon="inline-start" />
          {state.refreshing ? '更新中…' : '刷新'}
        </Button>
      </FieldGroup>

      <DownloadHistorySummary data={state.data} loading={state.loading} />
      {state.error && !state.data ? (
        <PageErrorNotice
          className="mt-6"
          message={state.error}
          onRetry={state.retry}
          retryLabel="重新加载"
          title="暂时无法读取下载记录"
        />
      ) : null}
      {state.error && state.data ? (
        <FeedbackNotice
          action={
            <Button onClick={state.retry} size="sm" variant="outline">
              重新加载
            </Button>
          }
          className="mt-6"
          description={state.error}
          title="下载记录刷新失败"
          tone="error"
        />
      ) : null}
      {actionError ? (
        <FeedbackNotice
          className="mt-6"
          description={actionError}
          title="操作未完成"
          tone="error"
        />
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
          onPageChange={(page) =>
            setHistory((current) => ({ ...current, page }))
          }
          page={page}
          pages={Math.ceil(state.data.total / state.data.page_size)}
        />
      ) : null}
    </div>
  );
}
