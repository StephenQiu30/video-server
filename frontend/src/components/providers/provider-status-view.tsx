'use client';

import { ArrowClockwiseIcon, WarningCircleIcon } from '@phosphor-icons/react';
import { type KeyboardEvent, useMemo, useState } from 'react';

import { BackLink } from '@/components/layout/back-link';
import { PageHeader } from '@/components/layout/page-header';
import { PagePagination } from '@/components/layout/page-pagination';
import { ProviderStatusItem } from '@/components/providers/provider-status-item';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { ItemGroup } from '@/components/ui/item';
import { RadioGroup, RadioGroupButtonItem } from '@/components/ui/radio-group';
import { Spinner } from '@/components/ui/spinner';
import { useProviderStatuses } from '@/hooks/useProviderStatuses';
import type { ProviderStatus } from '@/services/providers';

type StatusFilter = 'all' | 'available' | 'attention';
const STATUS_FILTERS: StatusFilter[] = ['all', 'available', 'attention'];
const STATUS_PAGE_SIZE = 8;
const EMPTY_PROVIDERS: ProviderStatus[] = [];

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
              <Spinner aria-hidden />
            ) : (
              <ArrowClockwiseIcon aria-hidden />
            )}
            {state.loading ? '刷新中…' : '刷新状态'}
          </Button>
        }
        description="先查看当前下载支持；需要时再展开单个平台，核对探针与真实任务证据。"
        title="平台状态"
        titleId="provider-status-title"
      />

      <div className="mt-10 space-y-6 sm:mt-12">
        {state.loading && !state.data ? (
          <StatusMessage label="正在加载平台状态" />
        ) : null}
        {state.error ? (
          <Alert variant="destructive">
            <WarningCircleIcon aria-hidden />
            <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
              {state.error}
              <Button onClick={state.retry} size="sm" variant="outline">
                <ArrowClockwiseIcon aria-hidden />
                重试
              </Button>
            </AlertDescription>
          </Alert>
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
              <RadioGroup
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
                  setFilter(value as StatusFilter);
                  setPage(1);
                }}
                value={filter}
              >
                <RadioGroupButtonItem value="all">全部</RadioGroupButtonItem>
                <RadioGroupButtonItem value="available">
                  当前可用
                </RadioGroupButtonItem>
                <RadioGroupButtonItem value="attention">
                  需关注
                </RadioGroupButtonItem>
              </RadioGroup>
            </div>
            {visibleProviders.length > 0 ? (
              <div className="space-y-5">
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

function matchesFilter(provider: ProviderStatus, filter: StatusFilter) {
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

  const currentIndex = STATUS_FILTERS.indexOf(target.value as StatusFilter);
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
