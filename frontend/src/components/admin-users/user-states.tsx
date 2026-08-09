import {
  ArrowClockwise,
  UsersThree,
  WarningCircle,
} from '@phosphor-icons/react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
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
        <Button variant="outline" size="sm" onClick={onRetry}>
          <ArrowClockwise />
          重试
        </Button>
      </AlertDescription>
    </Alert>
  );
}

export function EmptyUsers() {
  return (
    <div className="grid min-h-64 place-items-center border-y py-12 text-center">
      <div>
        <UsersThree
          className="mx-auto text-primary"
          size={36}
          weight="duotone"
        />
        <h2 className="mt-4 font-semibold">没有匹配的用户</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          尝试清空搜索词或更换筛选条件。
        </p>
      </div>
    </div>
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
