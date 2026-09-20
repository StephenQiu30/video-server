import { PageErrorNotice } from '@/components/layout/page-error-notice';
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';

export function AdminSkeleton({ rowsOnly = false }: { rowsOnly?: boolean }) {
  return (
    <div
      aria-label="正在加载用户列表"
      className="flex flex-col gap-6"
      role="status"
    >
      {!rowsOnly && (
        <>
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-20 w-full max-w-2xl" />
          <Skeleton className="h-16 w-full" />
        </>
      )}
      <div className="flex flex-col gap-2">
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
  return (
    <PageErrorNotice
      message={error}
      onRetry={onRetry}
      retryLabel="重新加载"
      title="暂时无法读取用户列表"
    />
  );
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
    <PageErrorNotice
      message="登录状态已失效，无法读取用户列表。"
      title="暂时无法读取用户列表"
    />
  );
}
