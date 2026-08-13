import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';

export function AnalyticsLoading() {
  return (
    <div aria-label="正在加载下载分析" className="space-y-12" role="status">
      <span className="sr-only">正在加载下载分析</span>
      <div className="hairline grid gap-8 border-y py-7 sm:grid-cols-2 xl:grid-cols-4">
        {['total', 'rate', 'users', 'bytes'].map((key) => (
          <div className="space-y-3" key={key}>
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-12 w-32" />
            <Skeleton className="h-3 w-40" />
          </div>
        ))}
      </div>
      <Skeleton className="h-72 w-full rounded-none" />
      <div className="grid gap-8 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-none" />
        <Skeleton className="h-64 rounded-none" />
      </div>
    </div>
  );
}

export function AnalyticsEmpty() {
  return (
    <Empty className="min-h-80 items-start rounded-none border-0 py-20 text-left">
      <EmptyHeader className="items-start">
        <EmptyTitle>当前周期还没有下载数据</EmptyTitle>
        <EmptyDescription className="text-left">
          切换统计周期，或等待用户创建下载任务后再查看。
        </EmptyDescription>
      </EmptyHeader>
    </Empty>
  );
}
