import { Suspense } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import DownloadRoute from '@/components/downloads/download-route';
import { BackLink } from '@/components/layout/back-link';
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
      <div className="mt-9 max-w-5xl">
        <Skeleton className="h-11 w-3/4" />
        <Skeleton className="mt-4 h-4 w-1/2" />
      </div>
      <div className="mt-8 grid items-start gap-10 lg:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.65fr)] lg:gap-16 xl:gap-24">
        <div>
          <Skeleton className="aspect-video w-full rounded-none" />
        </div>
        <div className="lg:pt-1">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="mt-5 h-9 w-4/5" />
          <Skeleton className="mt-4 h-5 w-full" />
          <Skeleton className="mt-8 h-11 w-full" />
          <Skeleton className="mt-7 h-11 w-3/4" />
        </div>
      </div>
    </div>
  );
}
