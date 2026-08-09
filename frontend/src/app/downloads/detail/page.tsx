import { Suspense } from 'react';

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
    <main className="content-shell space-y-6 py-12">
      <Skeleton className="h-6 w-32" />
      <div className="grid gap-10 lg:grid-cols-2">
        <Skeleton className="aspect-video w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    </main>
  );
}
