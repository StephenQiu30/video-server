import { Suspense } from 'react';
import { ProtectedRoute } from '@/components/auth/protected-route';
import DownloadRoute from '@/components/downloads/download-route';
import { PageNavigation } from '@/components/layout/page-navigation';
import { mediaFrameAspectRatio } from '@/components/media/media-cover';
import { mediaResultGridClassName } from '@/components/media/media-result';
import { AspectRatio } from '@/components/ui/aspect-ratio';
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
      <PageNavigation fallbackHref="/history" />
      <div className={mediaResultGridClassName}>
        <div>
          <AspectRatio ratio={mediaFrameAspectRatio}>
            <Skeleton className="size-full rounded-none" />
          </AspectRatio>
          <Skeleton className="mt-5 h-8 w-3/4" />
          <Skeleton className="mt-2 h-4 w-1/2" />
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
