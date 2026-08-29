import {
  ArrowClockwise,
  CheckCircle,
  Plus,
  WarningCircle,
} from '@phosphor-icons/react';
import { useMemo, useState } from 'react';

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

import type { CatalogResultState } from './model';
import {
  type CatalogVisibility,
  ProviderCatalogFilters,
} from './provider-catalog-filters';
import { ProviderCatalogList } from './provider-catalog-list';

const CATALOG_PAGE_SIZE = 10;

type ProviderCatalogScreenProps = {
  result: CatalogResultState;
  notice: string;
  onCreate: () => void;
  onDelete: (item: API.ProviderCatalogEntryResponse) => void;
  onEdit: (item: API.ProviderCatalogEntryResponse) => void;
  onRetry: () => void;
};

export function ProviderCatalogScreen({
  result,
  notice,
  onCreate,
  onDelete,
  onEdit,
  onRetry,
}: ProviderCatalogScreenProps) {
  const [query, setQuery] = useState('');
  const [visibility, setVisibility] = useState<CatalogVisibility>('all');
  const [page, setPage] = useState(1);
  const filtered = useMemo(
    () => filterCatalog(result.items, query, visibility),
    [query, result.items, visibility],
  );
  const pages = Math.max(1, Math.ceil(filtered.length / CATALOG_PAGE_SIZE));
  const currentPage = Math.min(page, pages);
  const visibleItems = filtered.slice(
    (currentPage - 1) * CATALOG_PAGE_SIZE,
    currentPage * CATALOG_PAGE_SIZE,
  );

  return (
    <section aria-busy={result.loading} className="space-y-10">
      <div>
        <BackLink className="mb-4" fallbackHref="/providers" />
        <PageHeader
          action={
            <Button onClick={onCreate}>
              <Plus aria-hidden />
              新增平台
            </Button>
          }
          description="维护平台状态页的名称、排序与可见性。下载域名和执行能力由系统 Profile 控制。"
          title="平台目录"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
        <p>
          共 <strong className="text-foreground">{result.items.length}</strong>{' '}
          个目录条目
        </p>
        <p>“仅目录”条目不会获得真实下载能力。</p>
      </div>

      {notice ? (
        <Alert variant="success">
          <CheckCircle aria-hidden />
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      ) : null}
      {result.error ? (
        <Alert variant="destructive">
          <WarningCircle aria-hidden />
          <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
            {result.error}
            <Button onClick={onRetry} size="sm" variant="outline">
              <ArrowClockwise aria-hidden />
              重试
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      {result.loading && result.items.length === 0 ? (
        <CatalogSkeleton />
      ) : result.items.length === 0 ? (
        <Empty className="hairline min-h-64 items-start rounded-none border-y py-14 text-left">
          <EmptyHeader className="items-start">
            <EmptyTitle>平台目录为空</EmptyTitle>
            <EmptyDescription className="text-left">
              新增条目后，可在平台状态页公开展示。
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : result.items.length > 0 ? (
        <div className="space-y-6">
          <ProviderCatalogFilters
            onQueryChange={(value) => {
              setQuery(value);
              setPage(1);
            }}
            onVisibilityChange={(value) => {
              setVisibility(value);
              setPage(1);
            }}
            query={query}
            visibility={visibility}
          />
          {visibleItems.length > 0 ? (
            <ProviderCatalogList
              items={visibleItems}
              onDelete={onDelete}
              onEdit={onEdit}
            />
          ) : (
            <Empty className="min-h-48 items-start rounded-none px-0 text-left">
              <EmptyHeader className="items-start">
                <EmptyTitle>没有匹配的平台</EmptyTitle>
                <EmptyDescription className="text-left">
                  调整搜索词或公开状态后重试。
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
            <span>
              显示 {visibleItems.length} 项，共 {filtered.length} 项
            </span>
            <PagePagination
              ariaLabel="平台目录分页"
              className="w-auto justify-end"
              compact
              onPageChange={setPage}
              page={currentPage}
              pages={pages}
            />
          </footer>
        </div>
      ) : null}
    </section>
  );
}

function filterCatalog(
  items: API.ProviderCatalogEntryResponse[],
  query: string,
  visibility: CatalogVisibility,
) {
  const normalized = query.trim().toLocaleLowerCase();
  return items.filter((item) => {
    const matchesQuery =
      !normalized ||
      item.display_name.toLocaleLowerCase().includes(normalized) ||
      item.key.toLocaleLowerCase().includes(normalized);
    const matchesVisibility =
      visibility === 'all' ||
      (visibility === 'visible' ? item.is_visible : !item.is_visible);
    return matchesQuery && matchesVisibility;
  });
}

function CatalogSkeleton() {
  return (
    <div
      aria-label="正在加载平台目录"
      className="hairline divide-y border-y"
      role="status"
    >
      {['first', 'second', 'third', 'fourth'].map((row) => (
        <div className="py-4" key={row}>
          <Skeleton className="h-12 w-full" />
        </div>
      ))}
    </div>
  );
}
