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
      <div>
        <Skeleton className="h-5 w-20" />
        <Skeleton className="mt-2 h-4 w-48" />
      </div>
      <div className="grid grid-cols-2 gap-8 lg:grid-cols-4">
        {['total', 'rate', 'users', 'bytes'].map((key) => (
          <div className="space-y-3" key={key}>
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-12 w-32" />
            <Skeleton className="h-3 w-full max-w-40" />
          </div>
        ))}
      </div>
      <Skeleton className="h-96 rounded-none" />
      <div className="grid gap-10 lg:grid-cols-3 lg:gap-12">
        {['status', 'completion', 'sources'].map((key) => (
          <div key={key}>
            <Skeleton className="h-5 w-24" />
            <Skeleton className="mt-2 h-4 w-48 max-w-full" />
            <Skeleton className="mt-6 h-52 rounded-none" />
          </div>
        ))}
      </div>
      <Skeleton className="h-80 rounded-none" />
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
