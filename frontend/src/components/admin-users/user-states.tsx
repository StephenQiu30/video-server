import { ArrowClockwise, WarningCircle } from '@phosphor-icons/react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
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
      <div className="hairline divide-y border-y">
        {['first', 'second', 'third', 'fourth', 'fifth'].map((row) => (
          <div className="hairline py-3" key={row}>
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
  return (
    <Alert variant="destructive">
      <WarningCircle />
      <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
        {error}
        <Button onClick={onRetry} size="sm" type="button" variant="outline">
          <ArrowClockwise />
          重试
        </Button>
      </AlertDescription>
    </Alert>
  );
}

export function EmptyUsers() {
  return (
    <Empty className="hairline min-h-64 rounded-none border-y py-14">
      <EmptyHeader>
        <EmptyTitle>没有匹配的用户</EmptyTitle>
        <EmptyDescription>尝试清空搜索词或更换筛选条件。</EmptyDescription>
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
