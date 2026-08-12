import {
  ArrowClockwise,
  CheckCircle,
  Plus,
  Stack,
  WarningCircle,
} from '@phosphor-icons/react';

import { BackLink } from '@/components/back-link';
import { PageHeader } from '@/components/page-header';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';

import type { CatalogResultState } from './model';
import { ProviderCatalogList } from './provider-catalog-list';

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
  return (
    <section className="space-y-10">
      <div>
        <BackLink className="mb-5 sm:mb-6" fallbackHref="/providers" />
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

      <div className="hairline flex flex-wrap items-center justify-between gap-4 border-y py-4 text-sm text-muted-foreground">
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
      {result.loading ? (
        <CatalogSkeleton />
      ) : result.error ? (
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
      ) : result.items.length === 0 ? (
        <Empty className="hairline min-h-64 rounded-none border-y py-14">
          <EmptyHeader>
            <EmptyMedia className="mb-3 text-muted-foreground">
              <Stack aria-hidden className="size-5" />
            </EmptyMedia>
            <EmptyTitle>平台目录为空</EmptyTitle>
            <EmptyDescription>
              新增条目后，可在平台状态页公开展示。
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <ProviderCatalogList
          items={result.items}
          onDelete={onDelete}
          onEdit={onEdit}
        />
      )}
    </section>
  );
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
