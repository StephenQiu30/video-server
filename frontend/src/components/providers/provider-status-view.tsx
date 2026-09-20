'use client';

import { ArrowClockwiseIcon } from '@phosphor-icons/react';
import { type KeyboardEvent, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { BackLink } from '@/components/layout/back-link';
import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { ProviderStatusItem } from '@/components/providers/provider-status-item';
import { useProviderStatuses } from '@/components/providers/use-provider-statuses';
import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { ItemGroup } from '@/components/ui/item';
import { Spinner } from '@/components/ui/spinner';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';

type StatusFilter = 'all' | 'available' | 'attention';
const STATUS_FILTERS: StatusFilter[] = ['all', 'available', 'attention'];
const STATUS_PAGE_SIZE = 8;
const EMPTY_PROVIDERS: API.ProviderListResponse['items'][number][] = [];
const PROVIDER_STATUS_ERROR_TOAST_ID = 'provider-status-refresh-error';

export function ProviderStatusView() {
  const state = useProviderStatuses();
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [page, setPage] = useState(1);
  const providers = state.data?.items ?? EMPTY_PROVIDERS;
  const available = providers.filter((item) => item.download_available).length;
  const filtered = useMemo(
    () => providers.filter((item) => matchesFilter(item, filter)),
    [filter, providers],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / STATUS_PAGE_SIZE));
  const currentPage = Math.min(page, pages);
  const visibleProviders = filtered.slice(
    (currentPage - 1) * STATUS_PAGE_SIZE,
    currentPage * STATUS_PAGE_SIZE,
  );

  useEffect(() => {
    if (!state.error || !state.data) {
      if (!state.error) toast.dismiss(PROVIDER_STATUS_ERROR_TOAST_ID);
      return;
    }

    toast.error('平台状态刷新失败', {
      action: {
        label: '重试',
        onClick: () => {
          toast.dismiss(PROVIDER_STATUS_ERROR_TOAST_ID);
          state.retry();
        },
      },
      description: state.error,
      id: PROVIDER_STATUS_ERROR_TOAST_ID,
    });
  }, [state.data, state.error, state.retry]);

  return (
    <section aria-labelledby="provider-status-title">
      <BackLink className="mb-4" fallbackHref="/" />
      <PageHeader
        action={
          <Button
            aria-label={state.loading ? '正在刷新平台状态' : '刷新状态'}
            className="disabled:opacity-100"
            disabled={state.loading}
            onClick={state.retry}
            variant="secondary"
          >
            {state.loading ? (
              <Spinner aria-hidden data-icon="inline-start" />
            ) : (
              <ArrowClockwiseIcon aria-hidden data-icon="inline-start" />
            )}
            {state.loading ? '刷新中…' : '刷新状态'}
          </Button>
        }
        description="先查看当前下载支持；需要时再展开单个平台，核对探针与真实任务证据。"
        title="平台状态"
        titleId="provider-status-title"
      />

      <div className="mt-10 flex flex-col gap-6 sm:mt-12">
        {state.loading && !state.data ? (
          <StatusMessage label="正在加载平台状态" />
        ) : null}
        {state.error && !state.data ? (
          <PageErrorNotice
            message={state.error}
            onRetry={state.retry}
            title="平台状态加载失败"
          />
        ) : null}
        {state.data ? (
          <>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted-foreground">
                共{' '}
                <strong className="text-foreground">{providers.length}</strong>{' '}
                个平台 · {available} 个当前可用 · {providers.length - available}{' '}
                个需关注
              </p>
              <ToggleGroup
                type="single"
                aria-label="筛选平台状态"
                className="flex w-auto flex-wrap items-center gap-1"
                onKeyDownCapture={(event) => {
                  const nextFilter = nextStatusFilter(event);
                  if (nextFilter) {
                    setFilter(nextFilter);
                    setPage(1);
                  }
                }}
                onValueChange={(value) => {
                  if (!value) return;
                  setFilter(value as StatusFilter);
                  setPage(1);
                }}
                value={filter}
              >
                <ToggleGroupItem data-filter="all" value="all">
                  全部
                </ToggleGroupItem>
                <ToggleGroupItem data-filter="available" value="available">
                  当前可用
                </ToggleGroupItem>
                <ToggleGroupItem data-filter="attention" value="attention">
                  需关注
                </ToggleGroupItem>
              </ToggleGroup>
            </div>
            {visibleProviders.length > 0 ? (
              <div className="flex flex-col gap-5">
                <ItemGroup aria-label="平台能力状态" className="gap-0">
                  {visibleProviders.map((provider) => (
                    <ProviderStatusItem
                      key={provider.key}
                      provider={provider}
                    />
                  ))}
                </ItemGroup>
                <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
                  <span>
                    显示 {visibleProviders.length} 项，共 {filtered.length} 项
                  </span>
                  <PagePagination
                    ariaLabel="平台状态分页"
                    className="w-auto justify-end"
                    compact
                    onPageChange={setPage}
                    page={currentPage}
                    pages={pages}
                  />
                </footer>
              </div>
            ) : (
              <Empty className="min-h-48 items-start px-0 text-left">
                <EmptyHeader className="items-start">
                  <EmptyTitle>没有匹配的平台</EmptyTitle>
                  <EmptyDescription className="text-left">
                    切换状态筛选，查看其他平台。
                  </EmptyDescription>
                </EmptyHeader>
              </Empty>
            )}
          </>
        ) : null}
      </div>
    </section>
  );
}

function matchesFilter(
  provider: API.ProviderListResponse['items'][number],
  filter: StatusFilter,
) {
  if (filter === 'available') return provider.download_available;
  if (filter === 'attention') return !provider.download_available;
  return true;
}

function nextStatusFilter(
  event: KeyboardEvent<HTMLDivElement>,
): StatusFilter | null {
  const direction =
    event.key === 'ArrowRight' || event.key === 'ArrowDown'
      ? 1
      : event.key === 'ArrowLeft' || event.key === 'ArrowUp'
        ? -1
        : 0;
  const target = event.target;
  if (
    direction === 0 ||
    !(target instanceof HTMLButtonElement) ||
    target.getAttribute('role') !== 'radio'
  ) {
    return null;
  }

  const currentIndex = STATUS_FILTERS.indexOf(
    target.dataset.filter as StatusFilter,
  );
  if (currentIndex < 0) {
    return null;
  }
  const nextIndex =
    (currentIndex + direction + STATUS_FILTERS.length) % STATUS_FILTERS.length;
  return STATUS_FILTERS[nextIndex];
}

function StatusMessage({ label }: { label: string }) {
  return (
    <div
      aria-label={label}
      className="flex min-h-40 items-center gap-2 text-sm text-muted-foreground"
      role="status"
    >
      <Spinner aria-hidden className="size-5" />
      <span>{label}</span>
    </div>
  );
}
