import { WarningCircle } from '@phosphor-icons/react';

import { PageErrorNotice } from '@/components/layout/page-error-notice';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';

export function AdminSkeleton({ rowsOnly = false }: { rowsOnly?: boolean }) {
  return (
    <div role="status" className="space-y-6" aria-label="正在加载用户列表">
      {!rowsOnly && (
        <>
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-20 w-full max-w-2xl" />
          <Skeleton className="h-16 w-full" />
        </>
      )}
      <div className="space-y-2">
        {['first', 'second', 'third', 'fourth', 'fifth'].map((row) => (
          <div className="py-3" key={row}>
            <Skeleton className="h-12 w-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function UsersLoadError({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => void;
}) {
  return <PageErrorNotice message={error} onRetry={onRetry} />;
}

export function EmptyUsers() {
  return (
    <Empty className="min-h-64 items-start rounded-none border-0 py-14 text-left">
      <EmptyHeader className="items-start">
        <EmptyTitle>没有匹配的用户</EmptyTitle>
        <EmptyDescription className="text-left">
          尝试清空搜索词或更换筛选条件。
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}

export function UnauthenticatedUsers() {
  return (
    <Alert variant="destructive">
      <WarningCircle />
      <AlertDescription>登录状态已失效，无法读取用户列表。</AlertDescription>
    </Alert>
  );
}
