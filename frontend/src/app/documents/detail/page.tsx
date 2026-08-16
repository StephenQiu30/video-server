import { Suspense } from 'react';

import { BackLink } from '@/components/back-link';
import { ProtectedRoute } from '@/components/protected-route';
import ScreenplayDocumentRoute from '@/components/screenplay-document-route';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = { title: '剧本文档详情' };

export default function DocumentDetailPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<RouteFallback />}>
        <ScreenplayDocumentRoute />
      </Suspense>
    </ProtectedRoute>
  );
}

function RouteFallback() {
  return (
    <div className="inner-page" role="status">
      <span className="sr-only">正在读取剧本文档</span>
      <BackLink fallbackHref="/documents" />
      <Skeleton className="mt-8 h-7 w-24" />
      <Skeleton className="mt-4 h-12 w-2/5" />
      <Skeleton className="mt-3 h-4 w-1/3" />
      <div className="mt-12 grid gap-12 lg:grid-cols-[minmax(0,1fr)_320px] lg:gap-0">
        <Skeleton className="h-[28rem] rounded-none lg:mr-12" />
        <Skeleton className="h-80 rounded-none lg:ml-12" />
      </div>
    </div>
  );
}
