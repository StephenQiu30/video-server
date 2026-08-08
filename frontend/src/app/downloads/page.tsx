import { Suspense } from 'react';

import DownloadRoute from '@/components/download-route';
import { Skeleton } from '@/components/ui/skeleton';

export const metadata = { title: '下载任务' };

export default function DownloadPage() {
  return (
    <Suspense fallback={<Skeleton className="m-10 h-[520px]" />}>
      <DownloadRoute />
    </Suspense>
  );
}
