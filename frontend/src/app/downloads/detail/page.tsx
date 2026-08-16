import { Suspense } from 'react';

import { BackLink } from '@/components/back-link';
import DownloadRoute from '@/components/download-route';
import { ProtectedRoute } from '@/components/protected-route';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = { title: '下载任务' };

export default function DownloadDetailPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<DetailSkeleton />}>
        <DownloadRoute />
      </Suspense>
    </ProtectedRoute>
  );
}

function DetailSkeleton() {
  return (
    <div className="inner-page">
      <BackLink fallbackHref="/history" />
      <Skeleton className="mt-7 h-10 w-40" />
      <div className="mt-10 grid gap-10 lg:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.75fr)] lg:gap-0">
        <div className="lg:pr-12">
          <Skeleton className="aspect-video w-full rounded-none" />
          <Skeleton className="mt-6 h-9 w-3/4" />
          <Skeleton className="mt-3 h-4 w-1/2" />
        </div>
        <div className="lg:border-l lg:pl-12">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="mt-8 h-24 w-full" />
          <Skeleton className="mt-8 h-20 w-full" />
          <Skeleton className="mt-8 h-11 w-full" />
        </div>
      </div>
    </div>
  );
}
