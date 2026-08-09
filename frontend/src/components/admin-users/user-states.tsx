import {
  ArrowClockwise,
  UsersThree,
  WarningCircle,
} from '@phosphor-icons/react';

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

export function AdminSkeleton({ rowsOnly = false }: { rowsOnly?: boolean }) {
  return (
    <div role="status" className="space-y-6" aria-label="正在加载用户列表">
      {!rowsOnly && (
        <>
          <Skeleton className="h-16 w-64" />
          <Skeleton className="h-11 w-full" />
        </>
      )}
      <div className="space-y-1 border-y py-2">
        {['first', 'second', 'third', 'fourth', 'fifth'].map((row) => (
          <Skeleton key={row} className="h-16 w-full" />
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
    <Empty className="min-h-64 rounded-none border-y py-12">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <UsersThree aria-hidden weight="duotone" />
        </EmptyMedia>
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
